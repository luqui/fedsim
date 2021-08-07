from recordclass import recordclass
from collections import namedtuple
from collections import defaultdict
import math
import random
import signal 
import sys
import time

Good = namedtuple('Good', ['name'])
QGood = namedtuple('QGood', ['good', 'qty'])

Ask = recordclass('Ask', ['price', 'qty', 'asker'])
Bid = recordclass('Ask', ['price', 'qty', 'bidder'])

class Market:
    def __init__(self, good, initialPrice, maxInventory):
        self.good = good
        self.maxInventory = maxInventory
        self.alpha = initialPrice / maxInventory

        self.askVolume = 0
        self.bidVolume = 0

        self.drift = 1 + math.exp(random.uniform(math.log(0.001), math.log(0.01)))

        self.inventory = 0

    def ask(self, qty):
        total = 0

        for i in range(qty):
            total += self.price()
            self.inventory += 1
            self.askVolume += 1

        return total

    def bid(self, qty, cap=float('inf')):
        total = 0
        bought = 0

        while bought < qty and self.inventory > 0 and self.price() <= cap:
            price = self.price()
            total += price
            cap -= price
            bought += 1
            self.inventory -= 1
            self.bidVolume += 1

        return (bought, total)

    def price(self):
        return self.alpha * max(0, self.maxInventory - self.inventory)

    def step(self):
        if self.inventory == 0:
            p = 1 - 2 * self.inventory / self.maxInventory
            self.alpha *= math.pow(self.drift, p)

    def report(self):
        volume = min(self.askVolume, self.bidVolume)
        self.askVolume -= volume
        self.bidVolume -= volume
        print(f'Market for {self.good}: ${self.price():.2f} - VOL {volume} - INV {self.inventory}')

        return volume

class Producer:
    def __init__(self, output, goodsRequired, scale):
        self.good = output.good
        self.quantityProduced = output.qty
        self.goodsRequired = goodsRequired
        self.scale = scale
        self.inventory = { req.good: 0 for req in goodsRequired }
        self.idleSteps = 0
        self.capital = 0
        self.alive = True

    def operate(self):
        self.idleSteps += 1

        self.inventory.setdefault(self.good, 0)
        if self.inventory[self.good] < self.scale * self.quantityProduced:
            scale = self.scale
            while scale > 0:
                scale -= 1
                for req in self.goodsRequired:
                    dq = req.qty - self.inventory[req.good]
                    if dq > 0:
                        received, cost = getMarket(req.good).bid(dq)
                        self.capital -= cost
                        self.inventory[req.good] += received

                    if self.inventory[req.good] < req.qty:
                        scale = 0
                        break
                else:
                    for req in self.goodsRequired:
                        self.inventory[req.good] -= req.qty
                    self.inventory[self.good] += self.quantityProduced

        market = getMarket(self.good)
        while self.inventory[self.good] * market.price() > max(0, -self.capital) and self.inventory[self.good] > 0:
            self.capital += market.ask(1)
            self.inventory[self.good] -= 1
            self.idleSteps = 0

    def report(self):
        reportLine = f'{self.quantityProduced} {self.good} <- '
        for req in self.goodsRequired:
            reportLine += f'{req.qty} {req.good}, '
        print(reportLine)
        print(f'    ${self.capital:0.2f} | {self.inventory}')


MARKETS = {}

def getMarket(good):
    m = MARKETS.get(good)
    if m is None:
        m = MARKETS[good] = Market(good, 1, 1000)
    return m

PRODUCERS = [
    Producer(QGood(Good('water'), 10), [ QGood(Good('labor'), 1) ], 1),
    Producer(QGood(Good('labor'), 1), [ QGood(Good('corn'), 1), QGood(Good('water'), 1) ], 1),
    Producer(QGood(Good('corn'), 10), [ QGood(Good('labor'), 1), QGood(Good('water'), 1) ], 1),
]

getMarket(Good('labor')).ask(100)
getMarket(Good('water')).ask(100)

GOODS = [ Good(s) for s in [ 'labor', 'water', 'corn', 'wheat', 'apples', 'wood', 'ore', 'house', 'meat', 'spear' ] ]

def make_producer():
    inputGoods = []
    inputGoods.append(QGood(Good('labor'), random.randrange(1,4)))

    goodsProduced = [ g for g in GOODS if g in MARKETS ]

    for i in range(random.randrange(0,4)):
        good = random.choice(goodsProduced)
        if any(g.good == good for g in inputGoods):
            continue
        inputGoods.append(QGood(good, random.randrange(1,4)))

    multiplier = random.randrange(1,10)
    return Producer(QGood(random.choice(GOODS), multiplier), inputGoods, 1)

ADD_PRODUCER = False

def add_producer(sig, frame):
    global ADD_PRODUCER
    ADD_PRODUCER = True
signal.signal(signal.SIGINT, add_producer)

STEP = 0
while True:
    for p in sorted(PRODUCERS, key=lambda _: random.uniform(0,1)):
        p.operate()

    for m in MARKETS.values():
        m.step()

    if ADD_PRODUCER:
        ADD_PRODUCER = False
        PRODUCERS.append(make_producer())
    if STEP % 50 == 0:
        PRODUCERS = list(filter(lambda p: p.alive, PRODUCERS))

    if STEP % 1 == 0:
        print()
        print(f'------ STEP {STEP} ------')
        for p in PRODUCERS:
            p.report()

        gdp = 0
        for g in sorted(MARKETS.keys()):
            gdp += MARKETS[g].report()

        print(f'GDP: {gdp}')
        time.sleep(0.05)

    STEP += 1
