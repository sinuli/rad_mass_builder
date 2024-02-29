import os
import imp
import types
import sys


def reload_package(package):

    fn = package.__file__
    fn_dir = os.path.dirname(fn) + os.sep
    module_visit = {fn}

    def reload_recursive_ex(module):
        imp.reload(module)
        for module_child in vars(module).values():
            if isinstance(module_child, types.ModuleType):
                fn_child = getattr(module_child, "__file__", None)
                if (
                    fn_child
                    and fn_child.startswith(fn_dir)
                    and fn_child not in module_visit
                ):
                    # print("reloading:", fn_child, "from", module)
                    module_visit.add(fn_child)
                    reload_recursive_ex(module_child)

    reload_recursive_ex(package)


def refresh_modules(kwarg):
    reloading_modules = [module for module in sys.modules if kwarg in module]
    for reloading_module in reloading_modules:
        sys.modules.pop(reloading_module)
