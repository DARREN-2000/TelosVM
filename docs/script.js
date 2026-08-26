// Full Compiler JS Implementation (Playground Version)

let compiledWasmBuffer = null;

function compileTelosToWAT(jsonStr) {
    let ast = JSON.parse(jsonStr);
    if (ast.type !== "Module") throw new Error("CompileError: Root node must be a 'Module'.");

    let variables = new Set();
    let watLines = [
        '(module',
        '  (import "env" "print" (func $print (param i32)))',
        '  (func $run (result i32)'
    ];
    let labelCounter = 0;
    
    // Pass 1: Semantic Verification
    function verifyScope(nodes) {
        for (let node of nodes) {
            if (node.type === "Declare") {
                if (variables.has(node.var)) throw new Error(`SemanticError: Variable '${node.var}' already declared.`);
                variables.add(node.var);
            } else if (node.type === "Assign") {
                if (!variables.has(node.var)) throw new Error(`Hallucination: Assigning to undeclared '${node.var}'.`);
                if (typeof node.value === "string" && !variables.has(node.value)) throw new Error(`Hallucination: Right hand undeclared '${node.value}'.`);
            } else if (node.type === "MathOp") {
                if (!variables.has(node.left)) throw new Error(`Hallucination: Undeclared '${node.left}'.`);
                if (!variables.has(node.right)) throw new Error(`Hallucination: Undeclared '${node.right}'.`);
                variables.add(node.target);
            } else if (node.type === "If") {
                if (!variables.has(node.condition_var)) throw new Error(`Hallucination: If condition '${node.condition_var}' undeclared.`);
                verifyScope(node.then_body);
                if (node.else_body) verifyScope(node.else_body);
            } else if (node.type === "While") {
                if (!variables.has(node.condition_var)) throw new Error(`Hallucination: While condition '${node.condition_var}' undeclared.`);
                verifyScope(node.body);
            } else if (node.type === "CallBuiltin") {
                if (!variables.has(node.arg_var)) throw new Error(`Hallucination: Calling print on undeclared '${node.arg_var}'.`);
            } else if (node.type === "Return") {
                if (!variables.has(node.var)) throw new Error(`Hallucination: Return var '${node.var}' undeclared.`);
            }
        }
    }
    verifyScope(ast.nodes);

    for (let v of variables) watLines.push(`    (local $${v} i32)`);

    // Pass 2: Code Gen
    function generate(nodes, ind) {
        for (let node of nodes) {
            if (node.type === "Declare") {
                watLines.push(`${ind}i32.const ${node.value}`);
                watLines.push(`${ind}local.set $${node.var}`);
            } else if (node.type === "Assign") {
                if (typeof node.value === "number") watLines.push(`${ind}i32.const ${node.value}`);
                else watLines.push(`${ind}local.get $${node.value}`);
                watLines.push(`${ind}local.set $${node.var}`);
            } else if (node.type === "MathOp") {
                watLines.push(`${ind}local.get $${node.left}`);
                watLines.push(`${ind}local.get $${node.right}`);
                if (node.operator === "add") watLines.push(`${ind}i32.add`);
                else if (node.operator === "sub") watLines.push(`${ind}i32.sub`);
                else if (node.operator === "mul") watLines.push(`${ind}i32.mul`);
                else if (node.operator === "div") watLines.push(`${ind}i32.div_s`);
                watLines.push(`${ind}local.set $${node.target}`);
            } else if (node.type === "If") {
                watLines.push(`${ind}local.get $${node.condition_var}`);
                watLines.push(`${ind}if`);
                generate(node.then_body, ind + "  ");
                if (node.else_body) {
                    watLines.push(`${ind}else`);
                    generate(node.else_body, ind + "  ");
                }
                watLines.push(`${ind}end`);
            } else if (node.type === "While") {
                let lbl = labelCounter++;
                watLines.push(`${ind}block $exit_${lbl}`);
                watLines.push(`${ind}  loop $loop_${lbl}`);
                watLines.push(`${ind}    local.get $${node.condition_var}`);
                watLines.push(`${ind}    i32.eqz`);
                watLines.push(`${ind}    br_if $exit_${lbl}`);
                generate(node.body, ind + "    ");
                watLines.push(`${ind}    br $loop_${lbl}`);
                watLines.push(`${ind}  end`);
                watLines.push(`${ind}end`);
            } else if (node.type === "CallBuiltin") {
                watLines.push(`${ind}local.get $${node.arg_var}`);
                watLines.push(`${ind}call $${node.function}`);
            } else if (node.type === "Return") {
                watLines.push(`${ind}local.get $${node.var}`);
                watLines.push(`${ind}return`);
            }
        }
    }
    generate(ast.nodes, "    ");

    watLines.push('    i32.const 0', '  )', '  (export "run" (func $run))', ')');
    return watLines.join('\n');
}

// UI Event Listeners
document.getElementById('compile-btn').addEventListener('click', () => {
    const jsonInput = document.getElementById('json-input').value;
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-dot');
    const watOutput = document.getElementById('wat-output');
    const runBtn = document.getElementById('run-btn');

    try {
        statusDot.className = 'status-indicator active';
        statusText.textContent = 'Verifying & Compiling...';
        
        const wat = compileTelosToWAT(jsonInput);
        
        watOutput.value = wat;
        statusDot.className = 'status-indicator success';
        statusText.textContent = 'Verification Passed! WAT Generated.';
        runBtn.disabled = false;
        
    } catch (e) {
        watOutput.value = "";
        statusDot.className = 'status-indicator error';
        statusText.textContent = e.message;
        runBtn.disabled = true;
    }
});

function logToTerminal(msg, type='log-msg') {
    const term = document.getElementById('terminal');
    term.innerHTML += `<span class="${type}">${msg}</span><br>`;
    term.scrollTop = term.scrollHeight;
}

document.getElementById('run-btn').addEventListener('click', async () => {
    const wat = document.getElementById('wat-output').value;
    logToTerminal("> Assembling WAT to Wasm binary...", "prompt");
    try {
        const wabt = await WabtModule();
        const wasmModule = wabt.parseWat('module.wat', wat);
        wasmModule.resolveNames();
        wasmModule.validate();
        
        const binaryOutput = wasmModule.toBinary({ log: true, write_debug_names:true });
        
        // FFI: Import JavaScript 'print' function into WebAssembly!
        const importObject = {
            env: {
                print: (val) => logToTerminal(`[WASM STDOUT]: ${val}`, "log-msg")
            }
        };
        
        const wasmInstance = await WebAssembly.instantiate(binaryOutput.buffer, importObject);
        
        logToTerminal("> Executing exported 'run' function...", "prompt");
        const result = wasmInstance.instance.exports.run();
        logToTerminal(`[EXECUTION RESULT]: ${result}`, "success");
        wasmModule.destroy();
    } catch (e) {
        logToTerminal(`[WASM ERROR]: ${e.message}`, "err-msg");
    }
});
