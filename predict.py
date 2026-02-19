

import numpy as np
from sklearn.linear_model import LinearRegression
import numpy as np
import pandas as pd
from sklearn.preprocessing import PolynomialFeatures
from sklearn.inspection import PartialDependenceDisplay
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt

#prediction module: take inputs, output forecast, output optimal parameters

#input variables: fan speed, water temp, relative humidity
#input format: 2D array of [dew_pt, fan_sp, water_temp]

#output variables: water production rate, energy consumption rate, optimal fan speed, optimal water temp

#predicition:
#--------------#
#regression 1 for water yeild - independent: dew point, fan speed, cooler temp, dependent: water yeild 
#regression 2 for energy useage - independent: dew point, fan speed, cooler temp, dependent: energy use
#include accuracy (R^2)

#optimization:
#--------------#
#grid search
#input: steps for fan settings and temp settings
#output: matrix for water yeild, matrix for energy use

#scoring
#input: previous output
#alg --> score = yeild/energy, highest score = optimal settings
#output: optimized pair: op_fan_sp, op_water_temp

#to start, navigate to the project folder and run "source venv/bin/activate"
#then run "pip install -r requirements.txt"
#to run a file (on mac) "python3 file.py"

#TODO 
#allow input from outside of this module
#train with better data
#add fan speed
#add headmap for optimization visualization

def train_regression_models(df, train,test, degree=2):
    """
    data: pandas DataFrame with columns
          ['dew_point', 'fan_speed', 'cooler_temp',
           'water_yield', 'energy_use']
    """
    #current vars: dew_point, coil_temp, water_output_hr, est_power

    # Independent variables
    X_train = train[['dew_point', 'coil_temp']] #removed fan speed because it is not in the data rn
    X_test = test[['dew_point', 'coil_temp']]
    # Dependent variables
    y_water_train = train['water_output_hr']
    y_energy_train = train['est_power']

    y_water_test = test['water_output_hr']
    y_energy_test = test['est_power']


    # # Models
    # water_model = LinearRegression()
    # energy_model = LinearRegression()

    #polynomial stuff
    #create pipelines

    energy_model = Pipeline([
        ('poly', PolynomialFeatures(degree=degree)),
        ('linear', LinearRegression())
    ])
    
    water_model = Pipeline([
        ('poly', PolynomialFeatures(degree=degree)),
        ('linear', LinearRegression())
    ])
    #fit models
    energy_model.fit(X_train, y_energy_train)
    water_model.fit(X_train, y_water_train)

    # fig = plt.figure()
    # ax = fig.add_subplot(111, projection='3d')
    # ax.scatter(X_train['dew_point'], X_train['coil_temp'], y_energy_train, c='blue')
    # ax.set_xlabel('Dew Point')
    # ax.set_ylabel('Coil Temp')
    # ax.set_zlabel('Energy Usage')
    # plt.show()

    #plot model with training data
    #currently we only have one coil temp.

    features = ['dew_point', 'coil_temp']   
    display = PartialDependenceDisplay.from_estimator(energy_model, X_test, features)
    plt.title("Interaction: Dew Point & Coil Temp vs. Energy Use")
    plt.show()


    # R² scores for training accuracy

    # #water yeild
    print(f"Training Score Water Model: {water_model.score(X_train, y_water_train)}")
    print(f"Testing Score Water Model: {water_model.score(X_test, y_water_test)}")

    # #energy use
    print(f"Training Score Energy Model: {energy_model.score(X_train, y_energy_train)}")
    print(f"Testing Score Energy Model: {energy_model.score(X_test, y_energy_test)}")



    
    return water_model, energy_model

def grid_search(models, dew_point, temp_steps): #add fan_steps later
    """
    models: (water_model, energy_model)
    dew_point: fixed dew point value
    fan_steps: array-like fan speed values
    temp_steps: array-like cooler temperature values
    """

    water_model, energy_model = models

    water_matrix = np.zeros((len(temp_steps)))
    energy_matrix = np.zeros((len(temp_steps)))

    #for i, fan in enumerate(fan_steps):
    for j, temp in enumerate(temp_steps):

        X = pd.DataFrame([[dew_point, temp]], columns=['dew_point', 'coil_temp']) #prevent error with mismatching df

        water_matrix[j] = water_model.predict(X)[0]
        energy_matrix[j] = energy_model.predict(X)[0]

    return water_matrix, energy_matrix

def score_settings(water_matrix, energy_matrix): #may have to adjust to make sure to score correctly
    """
    Returns:
    - score matrix
    - indices of optimal setting
    """

    # Avoid divide-by-zero
    score_matrix = np.divide(
        water_matrix,
        energy_matrix,
        out=np.zeros_like(water_matrix), #array where results will be stored
        where=energy_matrix != 0 # avoid divide by zero
    )

    max_index = np.unravel_index(
        np.argmax(score_matrix),
        score_matrix.shape
    )

    return score_matrix, max_index

if __name__ == "__main__":

    # Example dataset (replace with real data)
    df = pd.read_csv("data/cooling-chamber.csv")

    split_index = int(len(df) * 0.8)

    test = df.iloc[:split_index]
    train = df.iloc[split_index:]
    
    # Train models
    water_model, energy_model = train_regression_models(df,train,test)

    # Grid inputs
    #fan_steps = np.linspace(1, 5, 10) #1-5 with 10 steps
    temp_steps = np.linspace(5, 10, 10) 
    dew_point = 15  # fixed for optimization

    # Grid search
    water_mat, energy_mat = grid_search(
        (water_model, energy_model),
        dew_point,
        temp_steps
    )

    # Scoring --> input energy and water matrix at set dewpoint to find optimal fan and cooler temp
    score_mat, (j_opt) = score_settings(water_mat, energy_mat)

    # Optimal settings
    #op_fan_sp = fan_steps[i_opt]
    op_water_temp = temp_steps[j_opt]

   #print(f"Optimal Fan Speed: {op_fan_sp}")
    print(f"Optimal Cooler Temp: {op_water_temp}")
