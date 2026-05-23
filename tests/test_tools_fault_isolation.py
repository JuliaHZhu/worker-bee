"""#3 — A broken tool file must not prevent other tools from loading."""
import inspect



class TestToolsFaultIsolation:
    """Structural tests verifying main.py has per-file try/except around tool imports."""

    def test_main_py_has_per_file_try_except(self):
        """main.py must wrap each tool import in try/except so one bad file doesn't kill startup."""
        import main as main_module
        source = inspect.getsource(main_module)
        # The loading loop must contain a try/except around import_module
        assert "try:" in source
        assert "importlib.import_module" in source
        assert "except Exception" in source
        # And it must be inside the for-loop over pkgutil.iter_modules
        loop_start = source.find("for _, _mod_name, _ in pkgutil.iter_modules")
        loop_end = source.find("from agent import AIAgent")
        loop_body = source[loop_start:loop_end]
        assert "try:" in loop_body
        assert "except Exception" in loop_body

    def test_main_py_import_loop_prints_error(self):
        """The except block should print the failing module name to stderr."""
        import main as main_module
        source = inspect.getsource(main_module)
        assert "[Tool load error]" in source, "main.py missing user-visible error message for broken tools"
