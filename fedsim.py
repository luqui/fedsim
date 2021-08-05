from recordclass import recordclass
from collections import namedtuple
from collections import defaultdict
import math
import random
import time

Good = namedtuple('Good', ['name'])
Input = namedtuple('Input', ['good', 'price', 'qty'])

Ask = recordclass('Ask', ['price', 'qty', 'asker'])
Bid = recordclass('Ask', ['price', 'qty', 'bidder'])

class Market:
    def __init__(self, good):
        self.good = good
        self.asks = []
        self.bids = []
        self.volume = 0

    def ask(self, price, qty, asker):
        assert qty >= 0
        if qty == 0:
            return
        i = 0
        while i < len(self.asks):
            #if not self.asks[i].asker.alive:
            #    self.asks.pop(i)
            if price == self.asks[i].price and asker == self.asks[i].asker:
                self.asks[i].qty += qty
                break
            elif price < self.asks[i].price:
                self.asks.insert(i, Ask(price, qty, asker))
                break
            else:
                i += 1
        else:
            self.asks.append(Ask(price, qty, asker))

    def bid(self, price, qty, bidder):
        assert qty >= 0
        if qty == 0:
            return
        i = 0
        while i < len(self.bids):
            if not self.bids[i].bidder.alive:
                self.bids.pop(i)  
            elif price == self.bids[i].price and bidder == self.bids[i].bidder:
                self.bids[i].qty += qty
                break
            elif price > self.bids[i].price:
                self.bids.insert(i, Bid(price, qty, bidder))
                break
            else:
                i += 1
        else:
            self.bids.append(Bid(price, qty, bidder))

    def balance(self):
        self.volume = 0
        while self.asks and self.bids and self.bids[0].price >= self.asks[0].price:
            #if not self.asks[0].asker.alive:
            #    self.asks.pop(0)
            #    continue
            if not self.bids[0].bidder.alive:
                self.bids.pop(0)
                continue

            qty = min(self.bids[0].qty, self.asks[0].qty)
            price = (self.bids[0].price + self.asks[0].price) / 2
            self.bids[0].qty -= qty
            self.asks[0].qty -= qty

            self.bids[0].bidder.bought(self.good, qty, price)
            self.asks[0].asker.sold(self.good, qty, price)
            self.volume += qty

            if self.bids[0].qty == 0:
                self.bids.pop(0)
            if self.asks[0].qty == 0:
                self.asks.pop(0)

    def marketPrice(self):
        if self.asks and self.bids:
            return (self.asks[0].price + self.bids[0].price) / 2
        elif self.asks:
            return self.asks[0].price
        elif self.bids:
            return self.bids[0].price
        else:
            return None

    def report(self):
        askQty = 0
        bidQty = 0
        for ask in self.asks:
            # if ask.asker.alive:
                askQty += ask.qty
        for bid in self.bids:
            if bid.bidder.alive:
                bidQty += bid.qty

        reportLine = f'Market for {self.good}: VOL {self.volume} | '
        if self.asks:
            reportLine += f'ASK {askQty} ${self.asks[0].price:.2f} | '
        if self.bids:
            reportLine += f'BID {bidQty} ${self.bids[0].price:.2f}'

        print(reportLine)
        
        self.volume = 0

        assert self.asks == sorted(self.asks, key=lambda ask: ask.price)
        assert self.bids == sorted(self.bids, key=lambda bid: -bid.price)

class Logger:
    def __init__(self, name):
        self.name = name
        self.alive = True

    def bought(self, good, qty, price):
        print(f'{self.name} bought {qty} of {good} at ${price:.2f}')

    def sold(self, good, qty, price):
        print(f'{self.name} sold {qty} of {good} at ${price:.2f}')

class Producer:
    def __init__(self, good, multiplier, askPrice, goodsRequired, capital):
        self.good = good
        self.multiplier = multiplier
        self.askPrice = askPrice
        self.goodsRequired = goodsRequired
        self.capital = capital
        self.inventory = { req.good: 0 for req in goodsRequired }
        self.idleSteps = 0
        self.alive = True

    def operate(self, markets):
        self.idleSteps += 1
        if self.idleSteps > 200:
            self.alive = False
            return

        canProduce = True
        for req in self.goodsRequired:
            dq = req.qty - self.inventory[req.good]
            if dq > 0:
                markets.setdefault(req.good, Market(req.good)).bid(req.price, dq, self)
                self.capital -= dq * req.price
                canProduce = False

        if not canProduce:
            return

        for req in self.goodsRequired:
            self.inventory[req.good] -= req.qty
        
        markets.setdefault(self.good, Market(self.good)).ask(self.askPrice, self.multiplier, self)

    def bought(self, good, qty, price):
        assert qty > 0
        self.inventory[good] += qty

    def sold(self, good, qty, price):
        assert qty > 0
        self.capital += qty * price
        self.idleSteps = 0

    def report(self):
        reportLine = f'{self.good} for ${self.askPrice:.2f} <- '
        for req in self.goodsRequired:
            reportLine += f'{req.qty} {req.good} @{req.price:.2f}, '
        if self.multiplier != 1:
            reportLine += f'(makes {self.multiplier})'
        print(reportLine)
        #print(f'    ${self.capital:0.2f} | {self.inventory}')


MARKETS = {}
PRODUCERS = [
    Producer(Good('water'), 1, 0.00, [], 0),
    Producer(Good('labor'), 1, 1.00, [ Input(Good('corn'), 2.32, 1), Input(Good('water'), 2.22, 1) ], 0),
    Producer(Good('corn'), 10, 0.00, [ Input(Good('labor'), 1, 1), Input(Good('water'), 2.22, 1) ], 1000),
]

MARKETS[Good('labor')] = Market(Good('labor'))
MARKETS[Good('labor')].ask(0, 100, Logger('seed labor'))

GOODS = [ Good(s) for s in [ 'labor', 'water', 'corn', 'wheat', 'apples', 'wood', 'ore', 'house', 'meat', 'spear' ] ]

def make_producer():
    inputGoods = []
    cost = 0
    for i in range(random.randrange(1,4)):
        good = random.choice(GOODS)
        if any(g.good == good for g in inputGoods):
            continue
        price = MARKETS.setdefault(good, Market(good)).marketPrice()
        if price is None:
            price = random.uniform(0,10)
        inputGood = Input(good, round(max(0, price * random.uniform(0.5, 1.5) + random.uniform(-1, 1)), 2), random.randrange(1,4))
        cost += inputGood.price * inputGood.qty
        inputGoods.append(inputGood)

    multiplier = random.randrange(1,10)
    return Producer(random.choice(GOODS), multiplier, max(0, cost/multiplier + random.uniform(-1,1)), inputGoods, round(random.uniform(0, 100000), 2))

STEP = 0
while True:
    for p in PRODUCERS:
        p.operate(MARKETS)

    for m in MARKETS.values():
        m.balance()

    if STEP % 10 == 0:
        PRODUCERS.append(make_producer())
        PRODUCERS = list(filter(lambda p: p.alive, PRODUCERS))

    if STEP % 1 == 0:
        print()
        print(f'------ STEP {STEP} ------')
        for p in PRODUCERS:
            p.report()
        for g in sorted(MARKETS.keys()):
            MARKETS[g].report()
        time.sleep(0.1)

    STEP += 1
