from toybox.interventions.base import *
from toybox.interventions.core import * 

import copy
try:
  import ujson as json
except:
  import json
import re
import sys

from enum import Enum
"""An API for interventions on Breakout."""

def query_hack(query):
  # need replace all coll[i] with coll.collitem%04d.format(i)
  # can iterate over these, but will need to figure out string
  # interpolation for regex objects first
  if 'bricks' in query:
    search = re.search(r'bricks\[[0-9]+\]', query)
    if search is not None:
      before = search.group(0)
      i = int(re.search(r'[0-9]+', before).group(0))
      query = query.replace(before, 'bricks.brick{:04}'.format(i))
  
  if 'balls' in query:
    search = re.search(r'balls\[[0-9]+\]', query)
    if search is not None:
      before = search.group(0)
      i = int(re.search(r'[0-9]+', before).group(0))
      query = query.replace(before, 'balls.ball{:04}'.format(i))

  return query
  

class Breakout(Game):

  expected_keys = Game.expected_keys + ['paddle', 'is_dead', 'balls', 'ball_radius', 'paddle_speed', 'reset', 'bricks', 'paddle_width']
  immutable_fields = Game.immutable_fields + ['balls', 'bricks', 'reset']
  eq_keys = ['score'       ,
             'lives'       ,
             'level'       ,
             'paddle'      ,
             'reset'       ,
             'ball_radius' ,
             'bricks'      ,
             'balls'       ,
             'paddle_speed',
             'paddle_width',
             'is_dead'     ]

  coersions = { **Game.coersions, 
    'is_dead' : lambda x : x > 0.5,
    'reset' : lambda x : False if x is None else x > 0.5
  }

  def __init__(self, intervention : Intervention, 
    score=None, lives=None, rand=None, level=None, 
    paddle=None, paddle_width=None, paddle_speed=None,
    ball_radius=None, balls=None,
    bricks=None,
    reset=None, is_dead=None):

      super().__init__(intervention, score, lives, rand, level)
      self.reset = Breakout.coersions['reset'](reset)
      self.paddle = Paddle.decode(intervention, paddle, Paddle)
      self.ball_radius = ball_radius
      self.bricks = BrickCollection.decode(intervention, bricks, BrickCollection)
      self.balls = BallCollection.decode(intervention, balls, BallCollection)
      self.paddle_speed = paddle_speed
      self.paddle_width = paddle_width
      self.is_dead = Breakout.coersions['is_dead'](is_dead)
      self._in_init = False  

  def __copy__(self):
    return Breakout(
      self.intervention,
      score=self.score,
      lives=self.lives,
      rand=self.rand,
      level=self.level,
      paddle=self.paddle.encode(),
      paddle_width=self.paddle_width,
      paddle_speed=self.paddle_speed,
      ball_radius=self.ball_radius,
      bricks=self.bricks.encode(),
      balls=self.balls.encode(),
      is_dead=self.is_dead
    )  
  
  def sample(self, *queries):
    """Requires a seed state, hence an instance method"""
    if not self.intervention.modelmod: 
      log.warn('WARNING: no models for sampling')
      return 
    modelmod = self.intervention.modelmod
    mod = importlib.import_module(modelmod)
    if len(queries) == 0:
      return mod.sample(modelmod=modelmod, intervention=self.intervention)

    new = copy.copy(self)
    for query in queries:
      # this should work with the package argument, but right not it isn't
      # mod = importlib.import_module(query, package=modelmod)
      mod = importlib.import_module(modelmod + '.' + query_hack(query))
      val = mod.sample(intervention=self.intervention)
      if query in self.coersions: val = self.coersions[query](val)
      try:
        before = get_property(new, query)
        after = get_property(new, query, setval=val)
        logging.debug('Set {} to {} (was {})'.format(query, after, before))
      except AttributeError:
        coll = get_property(new, query)
        coll.clear()
        for item in val:
          coll.append(item)
        logging.info('reset', query)
    return new

  def make_models(modelmod, data):
    Game.make_models(modelmod, data)
    outdir = modelmod.replace('.', '/') + os.sep

    distr(outdir + 'ball_radius', [d.ball_radius for d in   data])
    distr(outdir + 'paddle_speed', [d.paddle_speed for d in data])
    distr(outdir + 'paddle_width', [d.paddle_width for d in data])

    distr(outdir + 'reset', [d.reset for d in   data])
    distr(outdir + 'is_dead', [d.reset for d in data])

    Paddle.make_models(modelmod, [d.paddle for d in data])
    BrickCollection.make_models(modelmod, [d.bricks for d in data])
    BallCollection.make_models(modelmod, [d.balls for d in data])

    with open(outdir + os.sep + '__init__.py', 'w') as f:
      f.write("""from ctoybox import Toybox
from toybox.interventions.breakout import BreakoutIntervention
from toybox.interventions.core import get_property, Collection
from . import * 
import importlib

def sample(*args, **kwargs):
  with Toybox('breakout') as tb:
    with BreakoutIntervention(tb) as intervention:
      game = intervention.game
      for key, v in vars(game).items():
        if key in game.immutable_fields and not isinstance(v, Collection): continue

        mod = importlib.import_module(kwargs['modelmod'] + '.' + key)
        val = mod.sample(**kwargs)
        if key in game.coersions: val = game.coersions[key](val)
        if __debug__: 
          before = get_property(game, key)

        if key in game.immutable_fields:
          v.clear()
          for item in val:
            v.append(item)
        else: 
          after = get_property(game, key, setval=val)
          if __debug__:
            print('Set {} to {} (was {})'.format(key, after, before))
      return game""")

class Paddle(BaseMixin):

  expected_keys = ['velocity', 'position']
  coersions = {
    # Otherwise, we get a wandering paddle...
    'velocity' : lambda v : Vec2D.decode(v.intervention, {'x': v.x, 'y': 0}, Vec2D)
  }
  eq_keys = expected_keys
  
  def __init__(self, intervention: Intervention, velocity, position):
    super().__init__(intervention)
    self.velocity = Vec2D.decode(intervention, velocity, Vec2D)
    self.position = Vec2D.decode(intervention, position, Vec2D)
    self._in_init = False  
    
  def __str__(self):
    return '<position: {}, velocity: {}>'.format(self.position, self.velocity)

  def make_models(modelmod, data):
    outdir = modelmod.replace('.', '/') + os.sep + 'paddle'
    Vec2D.make_models(outdir + os.sep + 'velocity', [d.velocity for d in data])
    Vec2D.make_models(outdir + os.sep + 'position', [d.position for d in data])

    with open(outdir + os.sep + '__init__.py', 'w') as f:
      f.write("""from . import velocity as v
from . import position as p
from toybox.interventions.breakout import Paddle

def sample(*args, **kwargs):
  obj = {'velocity' : v.sample(*args, **kwargs).encode(),
         'position' : p.sample(*args, **kwargs).encode()}
  intervention = kwargs['intervention'] if 'intervention' in kwargs else None
  return Paddle.decode(intervention, obj, Paddle)""")


  def sample(self, *queries):
    """Requires a seed state"""
    if not self.intervention.modelmod: 
      logging.warn('WARNING: no models for sampling')
      return 
    new = copy.copy(self)
    for query in queries:
      print('WARN: this might not work?')
      mod = importlib.import_module('.models.breakout.' + query, package=__package__)
      val = mod.sample(intervention=self.intervention)
      before = get_property(new, query)
      after = get_property(new, query, setval=val)
      logging.debug('Set {} to {} (was {})'.format(query, after, before))
    return new
    


class BrickCollection(Collection):

  def __init__(self, intervention : Intervention, bricks):
    super().__init__(intervention, bricks, Brick)
    self._in_init = False  

  def decode(intervention, bricks, clz):
    return BrickCollection(intervention, bricks)

  def make_models(modelmod, data):
    outdir = modelmod.replace('.', '/') + os.sep + 'bricks'

    max_bricks = max([len(d) for d in data])

    for i in range(max_bricks):
      Brick.make_models(outdir, i, [d[i] for d in data if len(d) > i])

    with open(outdir + os.sep + '__init__.py', 'w') as f:
        f.write("""import importlib
import os
from toybox.interventions.breakout import BrickCollection

def sample(*args, **kwargs):
  bricks = []
  intervention = kwargs['intervention'] if 'intervention' in kwargs else None
  for bricki in sorted(os.listdir(os.path.dirname(__file__))):
    if bricki.startswith('brick'):
      mod = importlib.import_module('{}.' + bricki)
      bricks.append(mod.sample(*args, **kwargs).encode())
  return BrickCollection.decode(intervention, bricks, BrickCollection)
        """.format(modelmod + '.bricks'))


class Brick(BaseMixin):

  expected_keys = ['destructible', 'depth', 'color', 'alive', 'points', 'size', 'position', 'row', 'col']
  eq_keys = expected_keys
  coersions = {
    'alive'        : lambda x : x > 0.5,
    'destructible' : lambda x : x > 0.5,
    'depth'        : lambda x : max(0, int(x)),
    'points'       : lambda x : max(0, int(x)),
    'row'          : lambda x : max(0, int(x)),
    'col'          : lambda x : max(0, int(x)),
    # 'size'         : lambda v2d : Vec2D.to_int(v2d),
    # 'position'     : lambda v2d : Vec2D.to_int(v2d)
  }
    
  def __init__(self, intervention, destructible, depth, color, alive, points, size, position, row, col):
    super().__init__(intervention)
    self.destructible = Brick.coersions['destructible'](destructible)
    self.depth = Brick.coersions['depth'](depth)
    self.color = Color.decode(intervention, color, Color)
    self.alive = Brick.coersions['alive'](alive)
    self.points = Brick.coersions['points'](points)
    self.size     = Vec2D.decode(intervention, size, Vec2D)
    self.position = Vec2D.decode(intervention, position, Vec2D)
    self.row = Brick.coersions['row'](row)
    self.col = Brick.coersions['col'](col)
    self._in_init = False

  def __repr__(self):
    return 'Brick({})'.format(' '.join([str(self.__dict__[key]) for key in Brick.expected_keys]))

  def __str__(self):
    return self.__repr__()

  def make_models(outdir, i, data): 
    outdir = outdir + os.sep + 'brick{:04d}'.format(i)

    distr(outdir + os.sep + 'destructible', [d.destructible for d in data])
    distr(outdir + os.sep + 'depth', [d.depth for d in data])
    Color.make_models(outdir + os.sep + 'color', [d.color for d in data])
    distr(outdir + os.sep + 'alive', [d.alive for d in data])
    distr(outdir + os.sep + 'points', [d.points for d in data])
    Vec2D.make_models(outdir + os.sep + 'size', [d.size for d in data])
    Vec2D.make_models(outdir + os.sep + 'position', [d.position for d in data])
    distr(outdir + os.sep + 'row', [d.row for d in data])
    distr(outdir + os.sep + 'col', [d.col for d in data])

    with open(outdir + os.sep + '__init__.py', 'w') as f:
      module = outdir.replace(os.sep, '.')
      f.write("""from . import * 
import os
import importlib
from toybox.interventions.base import BaseMixin
from toybox.interventions.breakout import Brick

def sample(*args, **kwargs):
  intervention = kwargs['intervention'] if 'intervention' in kwargs else None
  obj = dict()
  features = [os.path.splitext(f)[0] for f in os.listdir(os.path.dirname(__file__)) if not f.startswith('__')]
  for feature in features:
    mod = importlib.import_module('{}.' + feature)
    val = mod.sample(*args, **kwargs)
    obj[feature] = mod.sample(*args, **kwargs).encode() if isinstance(val, BaseMixin) else val
  return Brick.decode(intervention, obj, Brick)
      """.format(module))


class BallCollection(Collection):

  def __init__(self, intervention, balls):
    super().__init__(intervention, balls, Ball)
    self._in_init = False  

  def __str__(self):
    if len(self) == 1:
      return str(self[0])
    else:
      return '[{}]'.format(', '.join(str(b) for b in self))

  def make_models(modelmod, data):
    outdir = modelmod.replace('.', '/') + os.sep + 'balls'
    os.makedirs(outdir, exist_ok=True)

    max_balls = max([len(d) for d in data])

    for i in range(max_balls):
      Ball.make_models(outdir, i, [d[i] for d in data if len(d) > i])
    
    with open(outdir + os.sep + '__init__.py', 'w') as f:
      f.write("""import importlib
from toybox.interventions.breakout import BallCollection
import os

def sample(*args, **kwargs):
  balls = []
  intervention = kwargs['intervention'] if 'intervention' in kwargs else None
  for balli in sorted(os.listdir(os.path.dirname(__file__))):
    if balli.startswith('ball'):
      mod = importlib.import_module('{}.' + balli)
      balls.append(mod.sample(*args, **kwargs).encode())
  return BallCollection.decode(intervention, balls, BallCollection)
      """.format(modelmod + '.balls'))


class Ball(BaseMixin): 

  expected_keys = ['position', 'velocity']
  eq_keys = expected_keys

  def __init__(self, intervention, position, velocity):
    super().__init__(intervention)
    self.position = Vec2D.decode(intervention, position, Vec2D)
    self.velocity = Vec2D.decode(intervention, velocity, Vec2D)
    self._in_init = False  
    
  def __str__(self):
    return 'Ball(position: {}, velocity: {})'.format(self.position, self.velocity)

  def make_models(outdir, i, data):
    outdir = outdir + os.sep + 'ball{:04d}'.format(i)
    os.makedirs(outdir, exist_ok=True)

    Vec2D.make_models(outdir + os.sep + 'position', [d.position for d in data])
    Vec2D.make_models(outdir + os.sep + 'velocity', [d.velocity for d in data])

    with open(outdir + os.sep + '__init__.py', 'w') as f:
      module = outdir.replace(os.sep, '.')
      f.write("""from . import * 
import os
import importlib
from toybox.interventions.base import BaseMixin
from toybox.interventions.breakout import Ball

def sample(*args, **kwargs):
  intervention = kwargs['intervention'] if 'intervention' in kwargs else None
  obj = dict()
  features = [os.path.splitext(f)[0] for f in os.listdir(os.path.dirname(__file__)) if not f.startswith('__')]
  for feature in features:
    mod = importlib.import_module('{}.' + feature)
    val = mod.sample(*args, **kwargs)
    obj[feature] = mod.sample(*args, **kwargs).encode() if isinstance(val, BaseMixin) else val
  return Ball.decode(intervention, obj, Ball)
      """.format(module))


class BreakoutIntervention(Intervention):

    def __init__(self, tb: Toybox, modelmod=None, data=None, eq_mode=StandardEq):
        # check that the simulation in tb matches the game name.
        Intervention.__init__(self, tb, 'breakout', Breakout, modelmod=modelmod, data=data, eq_mode=eq_mode)

    def num_bricks_remaining(self):
        return sum([int(brick.alive) for brick in self.game.bricks])

    def num_bricks(self):
        return len(self.game.bricks)

    def num_rows(self):
        return len(self.config['row_scores'])

    def num_columns(self):
        """Returns the number of columns in the layout."""
        rows = self.num_rows()
        bricks = self.num_bricks()
        return bricks // rows

    def add_row(self, bricks, points, pre=None, post=None):
        """Adds the input row of bricks to the playing board.

        Parameters
        ====
        bricks: a list of brick objects
        value: the points associated with this row
        pre: add the list above
        post: add the list below
        """

        input_len = len(bricks)
        target_len = self.num_bricks()

        if input_len != target_len:
            raise ValueError('Input brick list length incorrect (is %d; should be %d)' % (input_len, target_len))

        if pre:
            for brick in bricks.reverse():
                self.bricks.insert(0, brick)
        
        elif post: 
            self.bricks.extend(bricks)

        else:
            raise ValueError('Must provide one optional argument: pre or post.')

        self.config['row_scores'].append(points)
        self.dirty_config = True

    def is_stack(self, bricks):
        col = bricks[0].col
        return all([b.col == col for b in bricks])

    def is_channel(self, bricklist):
        """Predicate indicating whether the input list of bricks constitutes a channel."""
        col = bricklist[0].col
        for brick in bricklist:
            if brick.col != col: return False
            if brick.alive: return False
        return True

    def get_column(self, i):
        """Returns the ith column of bricks."""
        bricks = []
        for brick in self.game.bricks:
            if brick.col == i:
                bricks.append(brick)
        return bricks
    
    def channel_count(self):
        count = 0
        for i in range(self.num_columns()):
            channel = self.get_column(i)
            if self.is_channel(channel): count += 1
        return count

    def get_ball_position(self):
        """Returns a list of positions, if there is more than one ball, and a single Vec2D object otherwise.:"""
        nballs = len(self.game.balls)
        if nballs > 1:
            return [ball.position for ball in self.game.balls]
        else:  
            return self.game.balls[0].position

    def get_ball_velocity(self):
        nballs = len(self.game.balls)
        if nballs > 1:
            return [ball.velocity for ball in self.game.balls]
        else:  
            return self.game.balls[0].velocity

    def get_paddle_position(self):
        return self.game.paddle.position

    def get_paddle_velocity(self):
        return self.game.paddle.velocity

    def find_brick(self, pred):
        for i, b in enumerate(self.game.bricks):
            if pred(b):
                return i, b
        raise ValueError('No bricks that satisfy the input predicate found.')

    def add_channel(self, i):
        """Turns the ith column into a channel"""
        for brick in self.game.bricks:
            if brick.col == i and brick.alive:
                brick.alive = False

    def fill_column(self, i): 
        """Fills the ith column, so that all bricks are now alive."""
        for brick in self.game.bricks:
            if brick.col == i and not brick.alive:
                brick.alive = True

    def find_channel(self):
        """Returns the first channel found."""
        for i in range(self.num_columns()):
            col = self.get_column(i)
            if self.is_channel(col):
                return i, col
        return -1, None

    def clear_board(self):
        """Clears the board of all bricks"""
        for brick in self.game.bricks:
            brick.alive = False


if __name__ == "__main__":
  import argparse , logging
  from ctoybox import Toybox, Input

  logging.basicConfig(level=logging.DEBUG)

  parser = argparse.ArgumentParser(description='test Breakout interventions')
  parser.add_argument('--partial_config', type=str, default="null")
  parser.add_argument('--save_json', type=bool, default=False)
  args = parser.parse_args()




