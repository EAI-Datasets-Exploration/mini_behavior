from gym_minigrid.roomgrid import *
from gym_minigrid.register import register
from gym_minigrid.objects import *
from gym_minigrid.transition_probs import create_transition_matrices

DEFAULT_OBJS = ['counter', 'plate', 'ashcan', 'hamburger', 'ball', 'apple', 'milk', 'juice', 'kiwi', 'grape', 'orange', 'bowl', 'egg', 'cucumber']

class TransitionEnv(RoomGrid):
    """
    """

    def __init__(
            self,
            objs=None,
            transition_probs=None,
            num_choose=4,
            mode='not_human',
            room_size=8,
            num_rows=2,
            num_cols=2,
            max_steps=10,
            seed=1337
    ):
        if objs is None:
            objs = DEFAULT_OBJS

        self.num_rooms = num_rows * num_cols

        # generate matrix
        if transition_probs is None:
            self.transition_probs = create_transition_matrices(objs, self.num_rooms)
        else:
            for obj in objs:
                assert obj in transition_probs.keys(), f'{obj} missing transition matrix'
                assert np.all(np.shape(transition_probs[obj]) == np.array([self.num_rooms, self.num_rooms])), f'{obj} matrix has incorrect dimensions'
            self.transition_probs = transition_probs

        # randomly pick num_choose objs
        self.seed(seed=seed)
        chosen_objs = self._rand_subset(objs, num_choose)

        # initialize num_objs, key=obj name (str), value=num of the obj (1)
        num_objs = {obj: 1 for obj in chosen_objs}

        super().__init__(mode=mode,
                         num_objs=num_objs,
                         room_size=room_size,
                         num_rows=num_rows,
                         num_cols=num_cols,
                         max_steps=max_steps,
                         seed=seed
                         )

        self.mission = 'find the objs as they transition between rooms'

        actions = {'left': 0,
                   'right': 1,
                   'forward': 2}

        self.actions = IntEnum('Actions', actions)

    def _gen_objs(self):
        # randomly place objs on the grid
        for obj in self.obj_instances.values():
            self.place_obj(obj)

    def step(self, action):
        super().step(action)

        # use transition prob to decide what room the obj should be in
        for obj in self.obj_instances.values():
            if obj.type != 'door':
                cur_room = self.room_num_from_pos(*obj.cur_pos) # int
                probs = self.transition_probs[obj.get_class()][cur_room]
                new_room = np.random.choice(self.num_rooms, 1, p=probs)[0] # int
                room_idx = self.room_idx_from_num(new_room) # tuple
                self.grid.remove(*obj.cur_pos, obj) # remove obj from grid
                self.place_in_room(*room_idx, obj) # add obj to grid

        obs = self.gen_obs()
        reward = self._reward()
        done = self._end_conditions()
        return obs, reward, done, {}

    def _end_conditions(self):
        return self.step_count == self.max_steps

    def _reward(self):
        if self._end_conditions():
            return 1
        else:
            return 0

register(
    id='MiniGrid-TransitionEnv-8x8x4-N2-v0',
    entry_point='gym_minigrid.envs:TransitionEnv',
)

register(
    id='MiniGrid-TransitionEnv-8x8x4-N2-v1',
    entry_point='gym_minigrid.envs:TransitionEnv',
    kwargs={'mode': 'human'}
)
