import Gaffer


class GafferSignal(object):
    __pre_task_changed = Gaffer.Signal2()
    __post_task_changed = Gaffer.Signal2()

    @classmethod
    def pre_task_changed(cls):
        return cls.__pre_task_changed
    
    @classmethod
    def post_task_changed(cls):
        return cls.__post_task_changed