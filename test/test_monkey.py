
from ltipassparams.monkey import monkey_patch


class MyClass:
    def hello(self):
        print("In original")
        return "Hello World!"

    @property
    def fruit(self):
        return "Apple"

    def sum(self, a, b):
        return a + b


@monkey_patch(MyClass, 'hello')
def hello(self, orig):
    print("In monkey patch")
    return orig() + " Hello Banana!"


@monkey_patch(MyClass, 'fruit')
def fruit(self, orig):
    return orig() + " Banana"


@monkey_patch(MyClass, 'sum')
def sum(self, orig, a, b):
    return orig(a, b) + 1


class TestMonkeyPatch:
    def test_patch_method(self):
        assert(MyClass().hello() == "Hello World! Hello Banana!")

    def test_patch_property(self):
        assert(MyClass().fruit == "Apple Banana")

    def test_with_args(self):
        assert(MyClass().sum(1, 2) == 4)