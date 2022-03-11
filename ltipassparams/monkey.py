
def monkey_patch(klass, methodname):
    " Creates a decorator to patch a method "
    def decorator(replacement):
        " Patches the method "
        original_method = getattr(klass, methodname)

        if isinstance(original_method, property):
            @property
            def wrapper(self):
                original_getter = lambda: original_method.fget(self)
                return replacement(self, original_getter)
        else:
            def wrapper(self, *args, **kwargs):
                bound_original = original_method.__get__(self, klass)
                return replacement(self, bound_original, *args, **kwargs)

        setattr(klass, methodname, wrapper)
        return wrapper
    return decorator

