import toybox
from toybox.envs.atari.base import ToyboxBaseEnv
from toybox.envs.atari.amidar import AmidarEnv
from toybox.envs.atari.breakout import BreakoutEnv
import gym

import multiprocessing
import sys
import time

from baselines.common.vec_env.vec_frame_stack import VecFrameStack
from baselines.common.cmd_util import make_vec_env
from baselines.common.atari_wrappers import DummyVecEnv, SubprocVecEnv

# Get innermost gym.Env (skip all Wrapper)
def _get_turtle(env):
    env = env
    while True:
        if (isinstance(env, VecFrameStack)):
            env = env.venv
        elif (isinstance(env, gym.wrappers.time_limit.TimeLimit)):
            # Not setting this causes issues later when trying
            # to time step with the TimeLimit wrapper. Not sure how to 
            # pass it in.
            env._max_episode_steps = 1e7
            env = env.env
        elif (isinstance(env, DummyVecEnv)):
            env = env.envs[0]
        elif isinstance(env, ToyboxBaseEnv):
            return env
        elif isinstance(env, SubprocVecEnv):
            env = env.example_env 
        elif (isinstance(env, gym.Wrapper)):
            env = env.env
        elif isinstance(env, gym.Env):
            return env
        else:
            raise ValueError("Can't unwrap", env)


def setUpToyboxGym(testclass, env_id, seed):
    nenv = 1
    frame_stack_size = 4
    env_type = 'atari'
 
    # Nb: OpenAI special cases acer, trpo, and deepQ.
    env = VecFrameStack(make_vec_env(env_id, env_type, nenv, seed) , frame_stack_size)
  
    testclass.env = env
    testclass.turtle = _get_turtle(env)
    testclass.toybox = testclass.turtle.toybox


def tearDownToyboxGym(testclass):
    testclass.env.close()


def stepEnv(self):
    obs, _, done, info = self.env.step(self.action)
    self.done = done if type(done) == 'bool' else done.any()
    self.obs = obs
    self.tick += 1

def resetEnv(self):
    self.getToybox().new_game()
    self.obs = self.env.reset()
