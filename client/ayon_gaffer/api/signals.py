import Gaffer


class GafferSignal(object):
    """
    A class to handle Gaffer signals for context changes.
    This class provides two class methods to access pre and post context change signals.
    Attributes:
        __pre_context_changed (Gaffer.Signal1): A signal that is emitted before the context changes.
        __post_context_changed (Gaffer.Signal1): A signal that is emitted after the context changes.
    Methods:
        pre_context_changed():
            Returns the signal that is emitted before the context changes.
        post_context_changed():
            Returns the signal that is emitted after the context changes.
    """
    __pre_context_changed = Gaffer.Signal1()
    __post_context_changed = Gaffer.Signal1()

    @classmethod
    def pre_context_changed(cls):
        """
        Method to access the pre-context changed signal.

        Returns:
            Signal: The pre-context changed signal.
        """
        return cls.__pre_context_changed
    
    @classmethod
    def post_context_changed(cls):
        """
        Method to access the post-context changed signal.

        Returns:
            Signal: The post-context changed signal.
        """
        return cls.__post_context_changed