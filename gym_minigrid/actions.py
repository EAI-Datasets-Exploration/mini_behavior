import numpy as np


def find_tool(env, possible_tool_types):
    # returns whether agent is carrying a obj of possible_tool_types, and the obj_instance
    for tool_type in possible_tool_types:
        tools = env.objs.get(tool_type, []) # objs of type tool in the env
        for tool in tools:
            if tool.check_abs_state(env, 'inhandofrobot'):
                return True
    return False


class BaseAction:
    def __init__(self, env):
        """
        initialize action
        """
        super(BaseAction, self).__init__()
        self.env = env
        self.key = None

    def can(self, obj):
        """
        check if possible to do action
        """

        # check if possible to do the action on the object
        if not obj.possible_action(self.key):
            return False

        # check if the object is in reach of the agent
        if not obj.check_abs_state(self.env, 'inreachofrobot'):
            return False

        return True

    def do(self, obj):
        """
        do action
        """
        assert self.can(obj), 'Cannot perform action'
        self.env.agent.obj = obj


class Close(BaseAction):
    def __init__(self, env):
        super(Close, self).__init__(env)
        self.key = 'close'

    def do(self, obj):
        super().do(obj)
        obj.states['openable'].set_value(False)
        obj.update(self.env)

        if obj.can_contain:
            for pos in obj.all_pos:
                objs = self.env.grid.get_all_objs(*pos)
                set_objs = [obj for obj in objs]
                for dim in obj.can_contain:
                    if objs[dim] is None:
                        set_objs[dim] = obj
                self.env.grid.set_all_objs(*pos, set_objs)


class Cook(BaseAction):
    def __init__(self, env):
        super(Cook, self).__init__(env)
        self.key = 'cook'
        self.tools = ['pan']
        self.heat_sources = ['stove']

    def can(self, obj):
        """
        can perform action if:
        - obj is cookable
        - agent is carrying a cooking tool
        - agent is infront of a heat source
        - the heat source is toggled on
        """
        if not super().can(obj):
            return False

        if find_tool(self.env, self.tools):
            front_cell = self.env.grid.get_all_objs(*self.env.agent.front_pos)
            # if isinstance(front_cell, list):
            for obj2 in front_cell:
                if obj2 is not None and obj2.type in self.heat_sources:
                    return obj2.check_abs_state(self.env, 'toggleable')
        return False

    def do(self, obj):
        super().do(obj)
        obj.states['cookable'].set_value(True)


class Drop(BaseAction):
    def __init__(self, env):
        super(Drop, self).__init__(env)
        self.key = 'drop'
        self.drop_dim = None

    def can(self, obj):
        """
        can drop obj if:
        - agent is carrying obj
        - there is no obj in base of forward cell
        """
        if not super().can(obj):
            return False

        if not obj.check_abs_state(self.env, 'inhandofrobot'):
            return False

        fwd_pos = self.env.agent.front_pos
        self.drop_dim = None
        for i in range(3):
            furniture, dim_obj = self.env.grid.get_dim(*fwd_pos, i)
            if furniture is None and dim_obj is None:
                self.drop_dim = i
                return True

        return False

    def do(self, obj):
        super().do(obj)
        fwd_pos = self.env.agent.front_pos

        # change object properties
        obj.cur_pos = fwd_pos
        # change agent / grid
        self.env.grid.set(*fwd_pos, obj, self.drop_dim)


class DropIn(BaseAction):
    def __init__(self, env):
        super(DropIn, self).__init__(env)
        self.key = 'drop_in'
        self.drop_dim = None

    def can(self, obj):
        """
        can drop obj under if:
        - agent is carrying obj
        - middle of forward cell is open
        - obj does not contain another obj
        """
        if not super().can(obj):
            return False

        if not obj.check_abs_state(self.env, 'inhandofrobot'):
            return False

        fwd_pos = self.env.agent.front_pos
        self.drop_dim = None
        for i in range(3):
            furniture, dim_obj = self.env.grid.get_dim(*fwd_pos, i)
            if furniture is not None and furniture.can_contain and dim_obj is None:
                self.drop_dim = i
                return True

        return False

    def do(self, obj):
        # drop
        super().do(obj)
        fwd_pos = self.env.agent.front_pos
        obj.cur_pos = fwd_pos
        self.env.grid.set(*fwd_pos, obj, self.drop_dim)

        # drop in and update
        furniture = self.env.grid.get_furniture(*fwd_pos, self.drop_dim)
        obj.states['inside'].set_value(furniture, True)


class Open(BaseAction):
    def __init__(self, env):
        super(Open, self).__init__(env)
        self.key = 'open'

    def do(self, obj):
        super().do(obj)
        obj.states['openable'].set_value(True)
        obj.update(self.env)

        if obj.can_contain:
            for pos in obj.all_pos:
                objs = self.env.grid.get_all_objs(*pos)
                set_objs = [obj for obj in objs]
                for dim in obj.can_contain:
                    if objs[dim] == obj:
                        set_objs[dim] = None
                self.env.grid.set_all_objs(*pos, set_objs)


class Pickup(BaseAction):
    def __init__(self, env):
        super(Pickup, self).__init__(env)
        self.key = 'pickup'

    def can(self, obj):
        if not super().can(obj):
            return False

        # cannot pickup if carrying
        if obj.check_abs_state(self.env, 'inhandofrobot'):
            return False

        # cannot pickup if inside closed obj
        # dim = self.env.grid.get_obj_dim(obj)
        # furniture = self.env.grid.get_furniture(*obj.cur_pos, dim)
        if obj.inside_of and not obj.inside_of.check_abs_state(self.env, 'openable'):
            return False

        return True

    def do(self, obj):
        def pick(obj1):
            self.env.grid.remove(*obj1.cur_pos, obj1)  # remove obj from the grid and unblock slots
            obj1.update_pos(np.array([-1, -1])) # update cur_pos of obj

            # check dependencies
            assert obj.check_abs_state(self.env, 'inhandofrobot')
            assert not obj.check_abs_state(self.env, 'onfloor')

            # pickup object inside
            if obj1.contains:
                pick(obj1.contains)

        super().do(obj)
        pick(obj)

        # if obj was inside, then no longer inside
        if obj.inside_of:
            obj.states['inside'].set_value(obj.inside_of, False)


class Slice(BaseAction):
    def __init__(self, env):
        super(Slice, self).__init__(env)
        self.key = 'slice'
        self.slicers = ['carving_knife', 'knife']

    def can(self, obj):
        """
        can perform action if:
        - action is sliceable
        - agent is holding a slicer
        """
        if not super().can(obj):
            return False
        return find_tool(self.env, self.slicers)

    def do(self, obj):
        super().do(obj)
        obj.states['sliceable'].set_value()


class Toggle(BaseAction):
    def __init__(self, env):
        super(Toggle, self).__init__(env)
        self.key = 'toggle'

    def do(self, obj):
        """
        toggle from on to off, or off to on
        """
        super().do(obj)
        cur = obj.check_abs_state(self.env, 'toggleable')
        obj.states['toggleable'].set_value(not cur)

