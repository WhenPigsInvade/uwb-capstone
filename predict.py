import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor 
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt
from sklearn.inspection import PartialDependenceDisplay
import joblib

#to start, navigate to the project folder and run "source venv/bin/activate"
#then run "pip install -r requirements.txt"
#to run a file (on mac) "python3 file.py"



#from test.py
#input current environment: amb_rh, amb_dew_pt, coil_in_temp

#output ideal: fan_speed, cooler_set_temp

def grid_search(models, amb_dew_pt, amb_rh, coil_in_temp, fan_steps, temp_steps):
    """
    Evaluates all combinations of fan speeds and cooler temperatures simultaneously.
    Returns 2D matrices for water yield and energy use.
    """
    water_model, energy_model = models

    # Create 2D matrices: shape is (len(fan_steps), len(temp_steps))
    water_matrix = np.zeros((len(fan_steps), len(temp_steps)))
    energy_matrix = np.zeros((len(fan_steps), len(temp_steps)))

    feature_cols = ['fan_speed', 'cooler_set_temp', 'coil_in_temp', 'amb_rh', 'amb_dew_pt']

    # Nested loop evaluates the entire 2D space
    for i, fan in enumerate(fan_steps):
        for j, temp in enumerate(temp_steps):
            # Form the exact 5-feature row required by scikit-learn
            X = pd.DataFrame([[fan, temp, coil_in_temp, amb_rh, amb_dew_pt]], columns=feature_cols)
            
            # Store predictions in the 2D grid coordinates
            water_matrix[i, j] = water_model.predict(X)[0]
            energy_matrix[i, j] = energy_model.predict(X)[0]

    return water_matrix, energy_matrix

def score_settings(water_matrix, energy_matrix):
    """
    Calculates the efficiency score (Water/Energy) across the 2D grid
    and finds the optimal matrix coordinates.
    """
    # Element-wise division to get efficiency (ml per Watt-hour)
    score_matrix = np.divide(
        water_matrix,
        energy_matrix,
        out=np.zeros_like(water_matrix),
        where=energy_matrix != 0
    )

    # np.argmax flattens the array by default, 
    # so np.unravel_index converts it back to 2D coordinates (row, col)
    opt_fan_idx, opt_temp_idx = np.unravel_index(
        np.argmax(score_matrix), 
        score_matrix.shape
    )

    return score_matrix, opt_fan_idx, opt_temp_idx

def predict(curr_fan_sp, curr_chiller_tp, curr_amb_dew_pt, curr_amb_rh, curr_coil_in_temp):

    # 1. Load trained models
    water_model = joblib.load("water_model.joblib")
    energy_model = joblib.load("energy_model.joblib")

    # 2. Define grid search bounds (higher resolution works great with 2D!)
    fan_steps = np.linspace(0, 5, 5)    # 0 to 5 with 5 variations
    temp_steps = np.linspace(0, 15, 15) #0 to 15 with 15 variations

    # 3. Perform 2D grid search
    water_mat, energy_mat = grid_search(
        (water_model, energy_model), 
        curr_amb_dew_pt, 
        curr_amb_rh,
        curr_coil_in_temp, 
        fan_steps, 
        temp_steps
    )

    # 4. Find the optimal 2D coordinate intersection
    score_mat, opt_fan_idx, opt_temp_idx = score_settings(water_mat, energy_mat)

    # 5. Extract the optimal hardware settings mapping to those indices
    pred_input = np.array([curr_fan_sp, curr_chiller_tp, curr_coil_in_temp, curr_amb_rh, curr_amb_dew_pt]).reshape(1,-1)
    curr_water_pred = water_model.predict(pred_input)
    curr_energy_pred = energy_model.predict(pred_input)
    
    op_fan_sp = fan_steps[opt_fan_idx]
    op_water_temp = temp_steps[opt_temp_idx]
    print("\n--- CURRENT RESULTS ---")
    print(f"Current Fan Setting: {curr_fan_sp}")
    print(f"Current Cooler Setting: {curr_chiller_tp}")
    print(f"Current Coil Inlet Temp: {curr_coil_in_temp}")
    print(f"Current Ambient Relative Humidity: {curr_amb_rh}")
    print(f"Current Ambient Dew Point {curr_amb_dew_pt}")
    
    print(f"Predicted System Yield: {(curr_water_pred[0]):.2f} ml/hr")
    print(f"Predicted 20 min Power Draw: {((curr_energy_pred[0]*(20/60))/1000):.2f} kWh")

    op_water_pred = water_mat[opt_fan_idx, opt_temp_idx]
    op_energy_pred = (((energy_mat[opt_fan_idx, opt_temp_idx])*(20/60))/1000)
    print("\n--- OPTIMIZATION RESULTS ---")
    print(f"Optimal Fan Speed Control: {op_fan_sp:.2f}")
    print(f"Optimal Cooler Set Temp:   {op_water_temp:.2f}°C")
    print(f"Maximized System Yield:    {op_water_pred:.2f} ml/hr")
    print(f"Minimized 20 min Power Draw:    {op_energy_pred:.2f} kWh")
    
    result = (op_water_temp, op_fan_sp, curr_water_pred, curr_energy_pred)
    return result
