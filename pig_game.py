from functools import update_wrapper
from collections import defaultdict
import random
import math

def decorator(d):
    "Make function d a decorator: d wraps a function fn."
    def _d(fn):
        return update_wrapper(d(fn), fn)
    update_wrapper(_d, d)
    return _d

@decorator
def memo(f):
    """Decorator that caches the return value for each call to f(args).
    Then when called again with same args, we can just look it up."""
    cache = {}
    def _f(*args):
        try:
            return cache[args]
        except KeyError:
            cache[args] = result = f(*args)
            return result
        except TypeError:
            # some element of args can't be a dict key
            return f(args)
    return _f

goal = 40
other = {1:0, 0:1}

def hold(state):
    """Apply the hold action to a state to yield a new state:
    Reap the 'pending' points and it becomes the other player's turn.
    p refers to the player whose turn it is"""
    (p, me, you, pending) = state
    return (other[p], you, me+pending, 0)
    
def roll(state, d):
    """Apply the roll action to a state (and a die roll d) to yield a new state:
    If d is 1, get 1 point (losing any accumulated 'pending' points),
    and it is the other player's turn. If d > 1, add d to 'pending' points."""
    (p, me, you, pending) = state
    if d == 1:
        return (other[p], you, me+1, 0) # pig out; other player's turn
    else:
        return (p, me, you, pending+d)  # accumulate die roll in pending
   

def clueless(state):
    "A strategy that ignores the state and chooses at random from possible moves."
    return random.choice(possible_moves)

def hold_at(x):
    """Return a strategy that holds if and only if 
    pending >= x or player reaches goal."""
    def strategy(state):
        p, me, you, pending = state
        return 'hold' if pending >= x or me + pending >= goal else 'roll'
    strategy.__name__ = 'hold_at(%d)' % x
    return strategy

goal = 50

def dierolls():
    "Generate die rolls."
    while True:
        yield random.randint(1, 6)

def play_pig(A, B, dierolls=dierolls()):
    """Play a game of pig between two players, represented by their strategies.
    Each time through the main loop we ask the current player for one decision,
    which must be 'hold' or 'roll', and we update the state accordingly.
    When one player's score exceeds the goal, return that player."""
    strategies = [A, B]
    state = (0, 0, 0, 0)
    while True:
        p, me, you, pending = state
        if me >= goal:
            return strategies[p]
        elif you >= goal:
            return strategies[other[p]]
        elif strategies[p](state) == 'hold':
            state = hold(state)
        else:
            action = strategies[p](state)
            if action == 'hold':
                state = hold(state)
            elif action == 'roll':
                state = roll(state, next(dierolls))
            else:
                return strategies[other[p]]

million = 1000000

def quality(state, action, utility):
    "The expected value of taking action in state, according to utility U."
    if action == 'hold':
        return utility(state + 1*million)
    if action == 'gamble':
        return utility(state + 3*million) * .5 + utility(state) * .5

def actions(state): return ['hold', 'gamble']

def identity(x): return x

U = math.log

def best_action(state, actions, Q, U):
    "Return the optimal action for a state, given utility."
    def EU(action): return Q(state, action, U)
    return max(actions(state), key=EU)
    
def Q_pig(state, action, Pwin):
    """The expected value of choosing action in state. Pwin is porobability of
    winning. If you win every time, the value would be 1. Pwin(hold(state)) in
    second line refers to opponent's probability of winning. That means our
    probability is 1 - that value. Top line in second return statement means that if
    you roll 1, then your pobability is the same as holding"""
    if action == 'hold':
        return 1 - Pwin(hold(state))
    if action == 'roll':
        return (1 - Pwin(roll(state, 1))
                + sum(Pwin(roll(state, d)) for d in (2,3,4,5,6))) / 6.
    raise ValueError

goal = 40

@memo
def Pwin(state):
    """The utility of a state; here just the probability that an optimal player
    whose turn it is to move can win from the current state."""
    # Assumes opponent also plays with optimal strategy.
    (p, me, you, pending) = state
    if me + pending >= goal:
        return 1
    elif you >= goal:
        return 0
    else:
        return max(Q_pig(state, action, Pwin)
                   for action in pig_actions(state))

def max_wins(state):
    "The optimal pig strategy chooses an action with the highest win probability."
    return best_action(state, pig_actions, Q_pig, Pwin)

def pig_actions(state):
    "The legal actions from a state."
    _, _, _, pending = state
    return ['roll', 'hold'] if pending else ['roll']

@memo
def win_diff(state):
    """The utility of a state: here the winning differential (pos or neg).
    Tells you difference in score after the game is over"""
    (p, me, you, pending) = state
    if me + pending >= goal or you >= goal:
        return (me + pending - you)
    else:
        return max(Q_pig(state, action, win_diff)
                   for action in pig_actions(state))

def max_diffs(state):
    """A strategy that maximizes the expected difference between my final score
    and my opponent's"""
    return best_action(state, pig_actions, Q_pig, win_diff)

goal = 40
states = [(0, me, you, pending)
          for me in range(41) for you in range(41) for pending in range(41)
          if me + pending <= goal]
r = defaultdict(int)
for s in states: r[max_wins(s), max_diffs(s)] += 1
print dict(r)

def story():
    """For all the states, group the states in terms of # of pending points in that
    state and for each number of pending points find how many times max_wins decided
    to roll vs how many times max_diffs rolls. Only consider times they differ."""
    r = defaultdict(lambda: [0, 0])
    for s in states:
        w, d = max_wins(s), max_diffs(s)
        if w != d:
            _, _, _, pending = s
            i = 0 if (w == 'roll') else 1
            r[pending][i] += 1
    for (delta, (wrolls, drolls)) in sorted(r.items()):
        print '%4d: %3d %3d' % (delta, wrolls, drolls)

def test_hold_at():
    assert hold_at(30)((1, 29, 15, 20)) == 'roll'
    assert hold_at(30)((1, 29, 15, 21)) == 'hold'
    assert hold_at(15)((0, 2, 30, 10))  == 'roll'
    assert hold_at(15)((0, 2, 30, 15))  == 'hold'
    return 'tests pass'
     
def test_hold_and_roll():    
    assert hold((1, 10, 20, 7))    == (0, 20, 17, 0)
    assert hold((0, 5, 15, 10))    == (1, 15, 15, 0)
    assert roll((1, 10, 20, 7), 1) == (0, 20, 11, 0)
    assert roll((0, 5, 15, 10), 5) == (0, 5, 15, 15)
    return 'tests pass'

def test_play_pig():
    A, B = hold_at(50), clueless
    rolls = iter([6,6,6,6,6,6,6,6,2]) 
    assert play_pig(A, B, rolls) == A
    return 'test passes'

def test_max_wins():
    assert(max_wins((1, 5, 34, 4)))   == "roll"
    assert(max_wins((1, 18, 27, 8)))  == "roll"
    assert(max_wins((0, 23, 8, 8)))   == "roll"
    assert(max_wins((0, 31, 22, 9)))  == "hold"
    assert(max_wins((1, 11, 13, 21))) == "roll"
    assert(max_wins((1, 33, 16, 6)))  == "roll"
    assert(max_wins((1, 12, 17, 27))) == "roll"
    assert(max_wins((1, 9, 32, 5)))   == "roll"
    assert(max_wins((0, 28, 27, 5)))  == "roll"
    assert(max_wins((1, 7, 26, 34)))  == "hold"
    assert(max_wins((1, 20, 29, 17))) == "roll"
    assert(max_wins((0, 34, 23, 7)))  == "hold"
    assert(max_wins((0, 30, 23, 11))) == "hold"
    assert(max_wins((0, 22, 36, 6)))  == "roll"
    assert(max_wins((0, 21, 38, 12))) == "roll"
    assert(max_wins((0, 1, 13, 21)))  == "roll"
    assert(max_wins((0, 11, 25, 14))) == "roll"
    assert(max_wins((0, 22, 4, 7)))   == "roll"
    assert(max_wins((1, 28, 3, 2)))   == "roll"
    assert(max_wins((0, 11, 0, 24)))  == "roll"
    return 'tests pass'

def test_win_diffs():
    assert(max_diffs((0, 36, 32, 5)))  == "roll"
    assert(max_diffs((1, 37, 16, 3)))  == "roll"
    assert(max_diffs((1, 33, 39, 7)))  == "roll"
    assert(max_diffs((0, 7, 9, 18)))   == "hold"
    assert(max_diffs((1, 0, 35, 35)))  == "hold"
    assert(max_diffs((0, 36, 7, 4)))   == "roll"
    assert(max_diffs((1, 5, 12, 21)))  == "hold"
    assert(max_diffs((0, 3, 13, 27)))  == "hold"
    assert(max_diffs((0, 0, 39, 37)))  == "hold"
    return 'tests pass'    

print test_hold_and_roll()
#print test_hold_at()
print test_max_wins()
print test_win_diffs()
print (max_wins((0, 11, 0, 24)))
