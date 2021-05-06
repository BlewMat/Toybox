from toybox import Toybox, Input
from toybox.envs.atari.base import ToyboxBaseEnv
from toybox.envs.atari.constants import *
import sys


class OthelloEnv(ToyboxBaseEnv):
    def __init__(self, frameskip=(0, 0), repeat_action_probability=0., grayscale=True, alpha=False):
        super().__init__(Toybox('othello', grayscale),
            frameskip, repeat_action_probability,
            grayscale=grayscale,
            alpha=alpha)