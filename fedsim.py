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

TRADE = 0
TRADEQTY = 0

def seqClosure(a, b):
    def r():
        a()
        b()
    return r
def cantBuyNothing():
    assert False

def marketBuy(markets, good, requested):
    buyClosure = lambda: None
    totalPrice = 0
    totalQty = 0
    while requested > 0:
        bestPrice = float('inf')
        bestQty = 0
        bestClosure = None
        bestMarket = None
        for m in markets:
            price, qty, closure = m.askPrice(good, requested)
            if qty == 0:
                continue
            pricePer = price / qty
            if pricePer < bestPrice:
                bestPrice = pricePer
                bestQty = qty
                bestClosure = closure
                bestMarket = m
        if bestMarket is None:
            break
        else:
            totalPrice += bestPrice * bestQty
            totalQty += bestQty
            requested -= bestQty
            buyClosure = seqClosure(buyClosure, bestClosure)
            
    return (totalPrice, totalQty, buyClosure)

def marketBuyMany(markets, inputs):
    buyClosure = lambda: None
    totalPrice = 0
    for i in inputs:
        price, qty, closure = marketBuy(markets, i.good, i.qty)
        assert qty <= i.qty
        if qty < i.qty:
            return (float('inf'), cantBuyNothing)
        totalPrice += price
        buyClosure = seqClosure(buyClosure, closure)
    return (totalPrice, buyClosure)

def make_params():
    return {
        'price_inertia': random.uniform(0,1),
        'scale_inertia': random.uniform(0,1),
        'price_inventory_base': random.uniform(1, 3),
        'profit_margin': random.uniform(0,0.2),
    }


class Producer:
    def __init__(self, output, inputs, capital, params, initialPrice = 1):
        self._output = output
        self._inputs = inputs
        self._price = initialPrice
        self._maxInventory = 30 * self._output.qty
        self._inventory = self._maxInventory // 2
        self._params = params
        self._capital = capital
        self._scale = 1

    def goodsProduced(self):
        if self._inventory > 0:
            return set([self._output.good])
        else:
            return set()

    def _priceScale(self):
        return math.pow(self._params['price_inventory_base'], 1 - 2 * self._inventory / self._maxInventory)

    def askPrice(self, good, qty):
        def buyClosure(price, qty):
            def r():
                assert self._inventory >= qty
                self._inventory -= qty
                self._capital += price
                global TRADE
                global TRADEQTY
                TRADE += price
                TRADEQTY += qty
            return r

        if good != self._output.good:
            return (float('inf'), 0, cantBuyNothing)
        else:
            q = min(qty, self._inventory)
            price = (1 + self._params['profit_margin']) * self._priceScale() * q * self._price
            return (price, q, buyClosure(price, q))

    def operate(self, markets):
        if self._inventory < self._maxInventory:
            totalPrice = 0
            rounds = 0
            for _ in range(round(self._scale)):
                price, buyClosure = marketBuyMany(markets, self._inputs)
                if price < self._capital:
                    self._capital -= price
                    buyClosure()
                    self._inventory += self._output.qty
                    totalPrice += price
                    rounds += 1
            if rounds > 0:
                averagePrice = totalPrice / rounds
                self._price = self._params['price_inertia'] * self._price + (1 - self._params['price_inertia']) * (averagePrice / self._output.qty)

        dScale = 1 - 2 * self._inventory / self._maxInventory
        self._scale = self._params['scale_inertia'] * self._scale + (1 - self._params['scale_inertia']) * max(1, self._scale + dScale)

    def reset(self):
        pass

    def report(self):
        reportLine = f'{self._output.qty} {self._output.good} @ ${self._priceScale() * self._price:.2f} <- '
        for req in self._inputs:
            reportLine += f'{req.qty} {req.good}, '
        print(reportLine)
        print(f'    ${self._capital:.2f} | {self._inventory} | scale {round(self._scale)}x')
        paramStr = ', '.join([f'{k}: {v:.2f}' for k,v in self._params.items()])
        print(f'    {paramStr}')

LABOR_PROFIT = 0.20
LABOR_PRICE_INERTIA = 0.9
class LaborUnion:
    def __init__(self, population, inputs, capital, initialPrice):
        self._population = population
        self._unemployment = population
        self._inputs = inputs
        self._price = initialPrice
        self._capital = capital

    def askPrice(self, good, qty):
        def buyClosure(price, qty):
            def r():
                self._capital += qty * price
                self._unemployment -= qty
            return r
        if good != Good('labor') or self._unemployment == 0:
            return float('inf'), 0, cantBuyNothing
        else:
            q = min(qty, self._unemployment)
            return self._price, q, buyClosure(self._price, q)

    def goodsProduced(self):
        return set([Good('labor')])

    def reset(self):
        self._unemployment = self._population

    def operate(self, markets):
        totalPrice = 0
        for _ in range(self._population):
            price, buyClosure = marketBuyMany(markets, self._inputs)
            if self._capital >= price:
                self._capital -= price
                totalPrice += price
                buyClosure()
            else:
                print(f'DEATH: can\'t afford ${price:.2f} with ${self._capital:.2f}')
                self._population -= 1

        if self._population > 0:
            costOfLiving = totalPrice / self._population
            # If I'm not making at least 1% of my total wealth, it's not worth it
            laborPrice = (1 + LABOR_PROFIT) * max(costOfLiving, 0.01 * self._capital / self._population)
            self._price = LABOR_PRICE_INERTIA * self._price + (1 - LABOR_PRICE_INERTIA) * laborPrice
        else:
            self._price = float('inf')

    def report(self):
        print(f'Population: {self._population} ({self._population - self._unemployment} employed) | Savings: ${self._capital:.2f} | Price: ${self._price:.2f}')


PRODUCERS = [
    LaborUnion(10, [ QGood(Good('corn'), 1), QGood(Good('water'), 1) ], capital=10000, initialPrice=1),
    Producer(QGood(Good('water'), 4), [ QGood(Good('labor'), 1) ], capital=1000, params=make_params(), initialPrice=1),
    Producer(QGood(Good('water'), 4), [ QGood(Good('labor'), 1) ], capital=1000, params=make_params(), initialPrice=1),
    Producer(QGood(Good('water'), 4), [ QGood(Good('labor'), 1) ], capital=1000, params=make_params(), initialPrice=1),
    Producer(QGood(Good('corn'), 4), [ QGood(Good('labor'), 1), QGood(Good('water'), 1) ], capital=1000, params=make_params(), initialPrice=1),
    Producer(QGood(Good('corn'), 4), [ QGood(Good('labor'), 1), QGood(Good('water'), 1) ], capital=1000, params=make_params(), initialPrice=1),
    Producer(QGood(Good('corn'), 4), [ QGood(Good('labor'), 1), QGood(Good('water'), 1) ], capital=1000, params=make_params(), initialPrice=1),
    ]

GOODS = [ Good(s) for s in [ 'labor', 'water', 'corn', 'wheat', 'apples', 'wood', 'ore', 'house', 'meat', 'spear' ] ]

def make_producer():
    inputGoods = []
    inputGoods.append(QGood(Good('labor'), random.randrange(1,4)))

    goodsProduced = list(set.union(*[ p.goodsProduced() for p in PRODUCERS ]))

    for i in range(random.randrange(0,4)):
        good = random.choice(goodsProduced)
        if any(g.good == good for g in inputGoods):
            continue
        inputGoods.append(QGood(good, random.randrange(1,4)))

    multiplier = random.randrange(1,10)
    return Producer(QGood(random.choice(GOODS), multiplier), inputGoods, 1000)

ADD_PRODUCER = False

def add_producer(sig, frame):
    global ADD_PRODUCER
    if ADD_PRODUCER:
        sys.exit(0)
    ADD_PRODUCER = True
signal.signal(signal.SIGINT, add_producer)

STEP = 0
while True:
    if STEP % 1 == 0:
        print()
        print(f'------ STEP {STEP} ------')
        for p in PRODUCERS:
            p.report()

        print(f'GDP: {TRADEQTY} @ ${TRADE:.2f}')
        TRADE = 0
        TRADEQTY = 0
        
        input()
        #time.sleep(0.4)

    for p in PRODUCERS:
        p.reset()

    for p in sorted(PRODUCERS, key=lambda _: random.uniform(0,1)):
        p.operate(PRODUCERS)

    if ADD_PRODUCER:
        ADD_PRODUCER = False
        PRODUCERS.append(make_producer())

    STEP += 1
