from .core import TelosExecutionError

class WasmExecutor:
    """Executes the compiled WebAssembly in a strict, zero-trust sandbox using Wasmtime."""
    @staticmethod
    def execute(wat_code: str, use_rich=False) -> int:
        try:
            import wasmtime
        except ImportError:
            raise TelosExecutionError("Wasmtime is not installed. Cannot execute server-side.")
            
        try:
            engine = wasmtime.Engine()
            store = wasmtime.Store(engine)
            module = wasmtime.Module(engine, wat_code)
            
            def host_print(*args):
                arg = args[-1] if args else 0
                if use_rich:
                    from rich import print as rprint
                    rprint(f"[bold green]> STDOUT (Wasm):[/bold green] [cyan]{arg}[/cyan]")
                else:
                    print(f"[TelosVM Server-Side Output]: {arg}")
            
            print_func = wasmtime.Func(store, wasmtime.FuncType([wasmtime.ValType.i32()], []), host_print)
            instance = wasmtime.Instance(store, module, [print_func])
            run = instance.exports(store).get("run")
            
            if run is None:
                raise TelosExecutionError("Exported 'run' function not found.")
            return run(store)
        except Exception as e:
            raise TelosExecutionError(f"Sandbox execution failed: {e}")
