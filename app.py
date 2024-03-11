import gradio as gr
import optuna
import numpy as np
# Turn off optuna logging
optuna.logging.set_verbosity(optuna.logging.WARNING)

def getHouseBill(
        maintenance, 
        num_month, 
        house_price, 
        house_rent, 
        cpi_inflation,
        tax_rate
    ):
    ans = 0
    rollout_maintenance = maintenance
    tax = tax_rate * house_price / 12
    rollout_tax = tax
    rollout_house_rent = house_rent
    bill_history = np.zeros((num_month, 4))
    for i in range(num_month):
        ans += rollout_maintenance + rollout_tax
        rollout_maintenance *= (1 + cpi_inflation/12)
        rollout_tax *= (1 + cpi_inflation/12)
        rollout_house_rent = rollout_house_rent * (1 + cpi_inflation/12)
        #print(f"The bill this month is: {ans:.0f} The maintenance is: {rollout_maintenance:.0f} The tax is: {rollout_tax:.0f}")
        bill_history[i, 0] = rollout_maintenance
        bill_history[i, 1] = rollout_tax
        bill_history[i, 2] = rollout_house_rent
    # Save the bills as a table
    #print(bill_history)
    #np.savetxt('./bills.txt', bill_history, fmt='%.0f', delimiter='\t', header='Maintenance, Tax, HouseRent')
    return bill_history

def getStockAdvance(cash, house_loan_monthly, maintenance_history, tax_history, house_rent_history, stock_inflation, num_month):
    ans = cash
    net_worth_history = np.zeros((num_month, 2))
    for i in range(num_month):
        increment = house_loan_monthly + maintenance_history[i] + tax_history[i] - house_rent_history[i]
        ans += increment
        #tmp_ans = ans
        ans *= (1 + stock_inflation/12)
        #print("Before: ", tmp_ans, "After: ", ans)
        net_worth_history[i, 0] = ans
        net_worth_history[i, 1] = increment
    #np.savetxt('./stock_net_worth.txt', net_worth_history, fmt='%d', header='Net worth of stock investment, increment', delimiter='\t')
    return ans

def getHouseNetWorth(
        house_price, 
        cash, 
        house_loan_monthly, 
        house_infaltion, 
        num_month, 
        decay_rate
    ):
    print("### House ###")
    print("House price: ", house_price)
    print("Cash: ", cash)
    print("House loan monthly: ", house_loan_monthly)
    total_cost = house_loan_monthly*num_month
    print("Total loan: ", total_cost)
    net_worth = house_price*((1+house_infaltion-decay_rate)**30)
    print("Net Worth with decay: ", net_worth)
    #net_worth = house_price*((1+house_infaltion)**30)
    #print("Net Worth without decay: ", net_worth)
    return total_cost, net_worth

def getStockNetWorth(cash, house_loan_monthly, maintenance_history, tax_history, house_rent_history, stock_inflation, num_month):
    print("### Stock ###")
    print("Cash: ", cash)
    rent_cost = np.sum(house_rent_history)
    print("Rent cost: ", rent_cost)
    total_investment = house_loan_monthly * num_month + cash - np.sum(house_rent_history - maintenance_history - tax_history)
    print("Total investment: ", total_investment)
    net_worth = getStockAdvance(cash, house_loan_monthly, maintenance_history, tax_history, house_rent_history, stock_inflation, num_month)
    print("Net worth: ", net_worth)
    return rent_cost, total_investment, net_worth

# Gradio interface
def stock_or_house(
    location,
    house_price,
    loan_ratio,
    loan_duration,
    management_cost,
    house_rent,
    interest_rate,
    house_inflation,
    stock_inflation,
    cpi_inflation,
    decay_rate,
    tax_rate
):
    # percentage to decimal
    interest_rate /= 100
    house_inflation /= 100
    stock_inflation /= 100
    cpi_inflation /= 100
    decay_rate /= 100

    # Run
    loan = house_price * loan_ratio
    cash = house_price * (1 - loan_ratio)
    study = optuna.create_study()
    def objective(trial):
        residual = loan
        x = trial.suggest_float('x', 0, 1e6)
        for d in range(loan_duration):    
            residual = residual - x + residual * interest_rate / 12
        return abs(residual)
    study.optimize(objective, n_trials=1000)
    house_loan_monthly = study.best_params['x']
    print("House loan monthly: ", house_loan_monthly)
    print("Residual: ", study.best_value)

    # Get the house bill
    maintenance = management_cost / 12
    bill_history = getHouseBill(maintenance, loan_duration, house_price, house_rent, cpi_inflation, tax_rate)
    house_total_loan, house_net_worth = getHouseNetWorth(house_price, cash, house_loan_monthly, house_inflation, loan_duration, decay_rate)
    rent_total_cost, stock_total_investment, stock_net_worth = getStockNetWorth(cash, house_loan_monthly, bill_history[:, 0], bill_history[:, 1], bill_history[:, 2], stock_inflation, loan_duration)
    stock_infos = f"初期投資金額是{cash:.0f}，\n總房租是{rent_total_cost:.0f}，\n總投資是{stock_total_investment:.0f}，\n最後的淨資產是{stock_net_worth:.0f}。\n"
    house_infos = f"購房時頭期款是{cash:.0f}，\n房子的總貸款是{house_total_loan:.0f}，\n每月房貸為{house_loan_monthly:.0f}，\n年稅金是每年房價的0.6%，\n最後的淨資產是{house_net_worth:.0f}。\n"
    main_msg = ""
    if stock_net_worth > house_net_worth:
        main_msg += "買股票比買房子划算。\n\n"
    else:
        main_msg += "買房子比買股票划算。\n\n"
    main_msg += "注意：每月房貸金額是由Optuna自動計算的，可能會有誤差。"
    return main_msg, house_infos, stock_infos

if __name__ == '__main__':
    demo = gr.Blocks()
    with demo:
        gr.Markdown(
            """# 買股票還是買房子? 
            ## 如果繳房貸的錢拿去買股票，會不會比買房子更划算? 這個程式會幫你找出答案。<br>
            買房的花費包括房貸、管理費、稅金、房屋折舊；<br>
            買股票的花費包括房租，以及股票的漲幅。<br>
            *買股票＋每月房租＝每月房貸＋管理費＋稅金*<br>
            如果每月房租超越了每月房貸＋管理費＋稅金，則從股票投資中取一部分的錢來補足房租。<br>
            地點不影響計算結果。<br>
            CPI是消費者物價指數，房租、管理費都會隨著CPI增加。<br>
            請輸入以下資訊：
            """
        )
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 買房子")
                location = gr.Textbox(label='地點(e.g. Taiwan)')
                house_price = gr.Number(label='房價(dollars)')
                loan_ratio = gr.Number(label='房貸比(0-1)')
                loan_duration = gr.Number(label='房貸期數(months)')
                management_cost = gr.Number(label='年管理費(%)')
            with gr.Column():
                gr.Markdown("### 買股票")
                house_rent = gr.Number(label='月房租(dollars)')
            with gr.Row():
                interest_rate = gr.Number(label='房貸年利率(%)')
                house_inflation = gr.Number(label='房價年通膨(%)')
                stock_inflation = gr.Number(label='股價年漲幅(%)')
                cpi_inflation = gr.Number(label='CPI年增率(%)')
                decay_rate = gr.Number(label='房屋年折舊率(%)')
                tax_rate = gr.Number(label='房屋稅率(%)')
        with gr.Row():
            computeButt = gr.Button("計算")
            result = gr.Textbox(label="結果")
            case_house = gr.Textbox(label="選擇買房子")
            case_stock = gr.Textbox(label="選擇買股票")
        computeButt.click(
            stock_or_house, 
            inputs=[
                location,
                house_price,
                loan_ratio,
                loan_duration,
                management_cost,
                house_rent,
                interest_rate,
                house_inflation,
                stock_inflation,
                cpi_inflation,
                decay_rate,
                tax_rate
            ],
            outputs=[result, case_house, case_stock]
        )
        gr.Examples(
            [
                ['Taiwan', 1.8e7, 0.8, 360, 3300*12, 30000, 2.15, 3, 6, 2, 1.4, 0.006],
            ],
            inputs=[
                location,
                house_price,
                loan_ratio,
                loan_duration,
                management_cost,
                house_rent,
                interest_rate,
                house_inflation,
                stock_inflation,
                cpi_inflation,
                decay_rate,
                tax_rate
            ]
        )
    demo.launch()