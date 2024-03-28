import shift
from time import sleep
from datetime import datetime, timedelta
import datetime as dt
from threading import Thread

#import pandas as pd

#########################################################################

#Important Global Variables

tickers = ['AAPL', 'CVX', 'DIS', 'GS', 'HD', 'IBM', 'JNJ', 'JPM', 'KO', 'MSFT', 'PG', 'VZ', 'WMT', 'XOM']
init_lot_size = 3
consecutive_loss_global = 5
consecutive_profit_global = 10
global_market_strategy_delay = 70
global_max_order_size = 8
global_rebate_for_market_strategy = 0.02
global_arbitrage_value = 0.05
global_code_working_time = 120
global_market_sell = False
global_time_between_iterations = 100
global_wait_for_order_filling = 60
global_wait_time_after_loss = 120
i=0

# Initialize dictionaries to track consecutive losses and profit for each ticker
consecutive_losses = {ticker: 0 for ticker in tickers}
consecutive_profits = {ticker: 0 for ticker in tickers}
order_sizes = {ticker: init_lot_size for ticker in tickers}
strategy_type = {ticker: 'long' for ticker in tickers}  # Initialize strategy type for each ticker

#########################################################################


def cancel_orders(trader, ticker):
    # cancel all the remaining orders
    for order in trader.get_waiting_list():
        if (order.symbol == ticker):
            trader.submit_cancellation(order)
            sleep(1)  # the order cancellation needs a little time to go through


def close_positions(trader, ticker):
    # NOTE: The following orders may not go through if:
    # 1. You do not have enough buying power to close your short postions. Your strategy should be formulated to ensure this does not happen.
    # 2. There is not enough liquidity in the market to close your entire position at once. You can avoid this either by formulating your
    #    strategy to maintain a small position, or by modifying this function to close ur positions in batches of smaller orders.

    # close all positions for given ticker
    print(f"running close positions function for {ticker}")

    item = trader.get_portfolio_item(ticker)
    
    # close any long positions
    long_shares = item.get_long_shares()
    if long_shares > 0:
        if long_shares < (global_max_order_size*100):
            print(f"limit selling at market because {ticker} long shares = {long_shares/100}")
            order = shift.Order(shift.Order.Type.LIMIT_SELL,
                                ticker, int(long_shares/100))  # we divide by 100 because orders are placed for lots of 100 shares
            trader.submit_order(order)
            print("NO PROFIT")
            global_market_sell = True
            sleep(global_wait_for_order_filling)  # we sleep to give time for the order to process
        else:
            print(f"MARKET selling because {ticker} long shares = {long_shares} because of overflow:")
            for _ in range(global_max_order_size):
                order = shift.Order(shift.Order.Type.MARKET_SELL,ticker, int(long_shares/1))  # we divide by 100 because orders are placed for lots of 100 shares
                trader.submit_order(order)
                print("LOSS")
            global_market_sell = True
            sleep(global_wait_time_after_loss)  # we sleep to give time for the order to process

    # close any short positions
    short_shares = item.get_short_shares()
    if short_shares > 0:
        if short_shares < (global_max_order_size*100):
            print(f"limit buying at market because {ticker} short shares = {short_shares/100}")
            for _ in range(global_max_order_size):
                order = shift.Order(shift.Order.Type.LIMIT_BUY,
                                    ticker, int(short_shares/1))
                trader.submit_order(order)
            print("NO PROFIT")
            global_market_sell = True
            sleep(global_wait_for_order_filling)
        else:
            print(f"MARKET buying because {ticker} long shares = {long_shares} because of overflow:")
            order = shift.Order(shift.Order.Type.MARKET_BUY,ticker, int(long_shares/100))  # we divide by 100 because orders are placed for lots of 100 shares
            trader.submit_order(order)
            print("LOSS")
            global_market_sell = True
            sleep(global_wait_time_after_loss)  # we sleep to give time for the order to process

        

def final_close_positions(trader, ticker):
    # NOTE: The following orders may not go through if:
    # 1. You do not have enough buying power to close your short postions. Your strategy should be formulated to ensure this does not happen.
    # 2. There is not enough liquidity in the market to close your entire position at once. You can avoid this either by formulating your
    #    strategy to maintain a small position, or by modifying this function to close ur positions in batches of smaller orders.

    # close all positions for given ticker
    print(f"running final close positions function for {ticker}")

    item = trader.get_portfolio_item(ticker)
    
    # close any long positions
    long_shares = item.get_long_shares()
    if long_shares > 0:
        print(f"market selling because {ticker} long shares = {long_shares/100}")
        order = shift.Order(shift.Order.Type.MARKET_SELL,
                            ticker, int(long_shares/100))  # we divide by 100 because orders are placed for lots of 100 shares
        trader.submit_order(order)
        sleep(1)  # we sleep to give time for the order to process

    # close any short positions
    short_shares = item.get_short_shares()
    if short_shares > 0:
        print(f"market buying because {ticker} short shares = {short_shares/100}")
        order = shift.Order(shift.Order.Type.MARKET_BUY,
                            ticker, int(short_shares/100))
        trader.submit_order(order)
        sleep(1)

    print("all positions closed")    

#def calculate_profit(trader, ticker, buy_order, sell_order):
    # Get executed prices for buy and sell orders
#    buy_executed_price = trader.get_last_price(buy_order.id)
#    sell_executed_price = trader.get_last_price(sell_order.id)

    # Calculate profit (positive if selling price > buying price)
#    profit = ((sell_executed_price - buy_executed_price) * buy_order.size) + global_rebate_for_market_strategy
#    return profit


def dynamic_market_making_strategy_buy_side(trader, ticker, endtime):
   # Get initial state
    

    # Define strategy parameters
    initial_order_size = init_lot_size  # Initial order size
    max_order_size = global_max_order_size # Maximum order size
    min_order_size = 1  # Minimum order size
    order_size_increment = 1  # Order size increment/decrement
    delay = global_market_strategy_delay  # Delay in seconds before selling
    consecutive_profit = 0  # Track consecutive profit for size adjustment
    consecutive_loss = 0  # Track consecutive loss for size adjustment

    order_size = initial_order_size  # Initialize order size

    while trader.get_last_trade_time() < endtime:
        # Get current best ask and best bid
        initial_bp = trader.get_portfolio_summary().get_total_bp()
        print(f"Initial buying power for {ticker}: {initial_bp}")
        best_price = trader.get_best_price(ticker)
        best_ask = best_price.get_ask_price()
        

        # Buy at best ask with a limit buy order
        buy_order = shift.Order(shift.Order.Type.LIMIT_BUY, ticker, order_size, price=best_ask)
        trader.submit_order(buy_order)
        buy_price = best_ask
        print(f"Placed buy order for {order_size} lots of {ticker} at price {best_ask}")


        print(f"Waiting for {delay} seconds before selling...")
        sleep(delay)

        best_bid = best_price.get_bid_price()

        # Determine sell price (limit sell at bought price or market sell at best bid, whichever is higher)
        sell_price = max(best_bid, buy_price) + global_arbitrage_value
        #sell_order_type = shift.Order.Type.LIMIT_SELL if sell_price == best_ask else shift.Order.Type.LIMIT_SELL
        sell_order_type = shift.Order.Type.LIMIT_SELL

        # Sell at determined price
        sell_order = shift.Order(sell_order_type, ticker, order_size, price=sell_price)
        trader.submit_order(sell_order)
        global_market_sell = False
        print(f"Waiting for {global_wait_for_order_filling} seconds to try and fill the sell order")
        sleep(global_wait_for_order_filling)
        close_positions(trader,ticker)
        #if ticker.get_realized_pl() == 0:
            #print("The strategy didnt give profit")
        #print(f"Placed sell order for {order_size} shares of {ticker} at price {sell_price}")

        # Update consecutive profit/loss for size adjustment
        if global_market_sell == False:
            consecutive_profit += 1
            consecutive_loss = 0
            print(consecutive_loss,"<-CONS. LOSS",consecutive_profit,"<-CONS. PROFIT")
        else:
            consecutive_profit = 0
            consecutive_loss += 1
            print(consecutive_loss,"<-CONS. LOSS",consecutive_profit,"<-CONS. PROFIT")

        # Adjust order size based on performance
        if consecutive_profit >= consecutive_profit_global:  # Increase order size after 3 consecutive profits
            order_size = min(order_size + order_size_increment, max_order_size)
            print(f"Increasing order size to {order_size} shares")
            consecutive_profit = 0
        elif consecutive_loss >= consecutive_loss_global:  # Decrease order size after 3 consecutive losses
            order_size = max(order_size - order_size_increment, min_order_size)
            print(f"Decreasing order size to {order_size} shares")
            consecutive_loss = 0

        #profit = sell_price - buy_price + global_rebate_for_market_strategy
        #print(f"Profit from trade: {profit}")    

        # Sleep for a short time before the next iteration
        
     

    print(f"Market making strategy for {ticker} finished.")


def market_making_strategy(trader, ticker, endtime, consecutive_losses, strategy_type):
    # Get initial state
    initial_bp = trader.get_portfolio_summary().get_total_bp()
    print(f"Initial buying power for {ticker}: {initial_bp}")

    # Define strategy parameters
    order_size = init_lot_size  # Adjust order size as needed
    delay = global_market_strategy_delay  # Delay in seconds before selling

    while trader.get_last_trade_time() < endtime:
        # Get current best ask and best bid
        best_price = trader.get_best_price(ticker)
        best_ask = best_price.get_ask_price()
        best_bid = best_price.get_bid_price()

        # Buy at best ask with a limit buy order
        buy_order = shift.Order(shift.Order.Type.LIMIT_BUY, ticker, order_size, price=best_ask)
        trader.submit_order(buy_order)
        print(f"Placed buy order for {order_size} shares of {ticker} at price {best_ask}")

        # Wait for the delay
        print(f"Waiting for {delay} seconds before selling...")
        sleep(delay)

        # Determine sell price (limit sell at bought price or market sell at best bid, whichever is higher)
        sell_price = max(best_bid, best_ask)
        sell_order_type = shift.Order.Type.LIMIT_SELL if sell_price == best_ask else shift.Order.Type.MARKET_SELL

        # Sell at determined price
        sell_order = shift.Order(sell_order_type, ticker, order_size, price=sell_price)
        trader.submit_order(sell_order)
        print(f"Placed sell order for {order_size} shares of {ticker} at price {sell_price}")

        # Update consecutive losses if needed (not applicable for market making)
        consecutive_losses[ticker] = 0

        # Sleep for a short time before the next iteration
        sleep(1)

    print(f"Market making strategy for {ticker} finished.")
    sleep(1)


def strategy(trader: shift.Trader, ticker: str, endtime):
    # NOTE: Unlike the following sample strategy, it is highly recommended that you track and account for your buying power and
    # position sizes throughout your algorithm to ensure both have adequate capital to trade throughout the simulation and
    # that you are able to close your position at the end of the strategy without incurring major losses.

    initial_pl = trader.get_portfolio_item(ticker).get_realized_pl()

    # Strategy parameters
    check_freq = 100
    order_size = init_lot_size  # NOTE: this is 5 lots which is 500 shares.
    ma_window = 25  # Moving average window

    # Strategy variables
    best_price = trader.get_best_price(ticker)
    best_ask = best_price.get_ask_price()
    previous_price = best_ask
    moving_average = previous_price
    prices = [previous_price]

    while trader.get_last_trade_time() < endtime:
        # Cancel unfilled orders from the previous time-step
        cancel_orders(trader, ticker)

        # Get necessary data
        best_price = trader.get_best_price(ticker)
        best_ask = best_price.get_ask_price()
        prices.append(best_ask)

        # Calculate moving average
        if len(prices) > ma_window:
            moving_average = sum(prices[-ma_window:]) / ma_window

        # Place order based on strategy
        if best_ask > moving_average:
            # Short if current ask is less than moving average
            if strategy_type[ticker] == 'long':  # Check current strategy type
                consecutive_losses[ticker] += 1  # Increment consecutive losses
                print(f"Longing {ticker} using strat 1 GTMA")
                if consecutive_losses[ticker] >= 5:  # Switch strategy if consecutive losses exceed threshold
                    strategy_type[ticker] = 'short'
                    print(f"Shorting {ticker} using strat 1 GTMA")
                    consecutive_losses[ticker] = 0  # Reset consecutive losses
            order = shift.Order(shift.Order.Type.LIMIT_SELL, ticker, order_size)
            #sleep(100)
            #order = shift.Order(shift.Order.Type.MARKET_BUY, ticker, order_size)
            trader.submit_order(order)
        else:
            # Long if current ask is higher than moving average
            if strategy_type[ticker] == 'short':  # Check current strategy type
                consecutive_losses[ticker] += 1  # Increment consecutive losses
                if consecutive_losses[ticker] >= 5:  # Switch strategy if consecutive losses exceed threshold
                    strategy_type[ticker] = 'long'
                    consecutive_losses[ticker] = 0  # Reset consecutive losses
            order = shift.Order(shift.Order.Type.LIMIT_BUY, ticker, order_size)
            #sleep(100)
            #order = shift.Order(shift.Order.Type.MARKET_SELL, ticker, order_size)
            trader.submit_order(order)

        previous_price = best_ask
        sleep(check_freq)

    # Cancel unfilled orders and close positions for this ticker
    cancel_orders(trader, ticker)
   

    #print(f"total profits/losses for {ticker}: {trader.get_portfolio_item(ticker).get_realized_pl() - initial_pl}")
    #sleep(100)
    close_positions(trader, ticker)



def main(trader):
   
    # Initialize consecutive losses and strategy type dictionaries
    #consecutive_losses = {ticker: 5 for ticker in tickers}
    #strategy_type = {ticker: 'long' for ticker in tickers}

    # Track overall initial profits/losses value to see how the strategy affects it
    initial_pl = trader.get_portfolio_summary().get_total_realized_pl()

    # Define start and end times for the trading session
    check_frequency = 60
    current = trader.get_last_trade_time()
    start_time = current
    end_time = start_time + timedelta(minutes=global_code_working_time)

    while trader.get_last_trade_time() < start_time:
        print("Still waiting for market open")
        sleep(check_frequency)

    # Initialize threads for running strategies for each ticker
    threads = []
    for ticker in tickers:
        
        #threads.append(Thread(target=final_close_positions, args=(trader, ticker)))
        threads.append(Thread(target=dynamic_market_making_strategy_buy_side, args=(trader, ticker, end_time)))
        # Market making strategy

        #threads.append(Thread(target=market_making_strategy, args=(trader, ticker, end_time, consecutive_losses, strategy_type)))
        # static market making strategy

    i=1
    j=1
    # Start all threads
    for thread in threads:
        thread.start()
        sleep(1)
        if j%14 == 0:
            print(f"The Current iteration is: {i}")
            print("")
            print("")
            i=i+1
            print(f"Waiting till {global_time_between_iterations} seconds before putting in next iteration.")
            sleep(global_time_between_iterations)
        j = j+1    

    # Wait until end time is reached
    while trader.get_last_trade_time() < end_time:
        sleep(check_frequency)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # Cancel unfilled orders and close positions for each ticker
    for ticker in tickers:
        cancel_orders(trader, ticker)
        final_close_positions(trader, ticker)

    print("END")
    print(f"Final BP: {trader.get_portfolio_summary().get_total_bp()}")
    print(f"Final Profits/Losses: {trader.get_portfolio_summary().get_total_realized_pl() - initial_pl}")
    sleep(1)



if __name__ == '__main__':
    with shift.Trader("arbhounders_test000") as trader:        
        trader.connect("initiator.cfg", "1ASCI6Fp")
        sleep(1)
        trader.sub_all_order_book()
        sleep(1)
        
        main(trader)


