import Gaffer


class GafferSignal(object):
    __pre_context_changed = Gaffer.Signal1()
    __post_context_changed = Gaffer.Signal1()

    @classmethod
    def pre_context_changed(cls):
        return cls.__pre_context_changed
    
    @classmethod
    def post_context_changed(cls):
        return cls.__post_context_changed