import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor # or Classifier
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt
from sklearn.inspection import PartialDependenceDisplay

def train_model():
    # Load your data
    df = pd.read_csv('test_data_5_25.csv')

    # Define your 5 inputs and 1 output
    X = df[['fan_speed', 'cooler_set_temp', 'coil_in_temp', 'amb_rh', 'amb_dew_pt']]
    y_water = df['water_flowrate']
    y_energy = df['energy_use']

    # Split into training (80%) and testing (20%) sets
    X_train, X_test, y_train_water, y_test_water = train_test_split(X, y_water, test_size=0.2, random_state=42)

    X_train, X_test, y_train_energy, y_test_energy = train_test_split(X, y_energy, test_size=0.2, random_state=42)

    # Initialize the model
    water_model = RandomForestRegressor(n_estimators=100, random_state=42)
    energy_model = RandomForestRegressor(n_estimators=100, random_state=42)

    # Train the model
    water_model.fit(X_train, y_train_water)
    energy_model.fit(X_train, y_train_energy)

    # Make predictions
    curr_water_prediction = water_model.predict(X_test)
    curr_energy_prediction = energy_model.predict(X_test)

    # Evaluate (for Regression)
    print(f"Water Prediction R-squared: {r2_score(y_test_water, curr_water_prediction):.2f}")
    print(f"Water Prediction Mean Absolulte Error (MAE:) {mean_absolute_error(y_test_water, curr_water_prediction):.2f} ml/hr")

    print(f"Energy Prediction R-squared: {r2_score(y_test_energy, curr_energy_prediction):.2f}")
    print(f"Energy Prediction Mean Absolulte Error (MAE:) {mean_absolute_error(y_test_energy, curr_energy_prediction):.2f} W")

    # Extract importance and match with variable names
    water_importances = water_model.feature_importances_
    feature_names = ['fan_speed', 'cooler_set_temp', 'coil_in_temp', 'amb_rh', 'amb_dew_pt']
    forest_importances_water = pd.Series(water_importances, index=feature_names)

    energy_importances = energy_model.feature_importances_
    forest_importances_energy = pd.Series(energy_importances, index=feature_names)

    # # Plot
    # fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(12,5))
    # forest_importances_water.sort_values(ascending=False).plot.bar(ax=ax[0])

    # ax[0].set_ylim([0,0.7])
    # ax[0].set_title("Feature Importance for Water Flow Rate Prediction")
    # ax[0].set_ylabel("Mean decrease in impurity")

    # forest_importances_energy.sort_values(ascending=False).plot.bar(ax=ax[1])
    # ax[1].set_ylim([0,0.7])
    # ax[1].set_title("Feature Importance for Energy Use (W) Prediction")
    # ax[1].set_ylabel("Mean decrease in impurity")
    # plt.show()

    # # Display PDP for the top variables (no error bars)
    # fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(15,6))

    # water_pdd = PartialDependenceDisplay.from_estimator(water_model, X_test, [0, 1, 2, 3, 4],ax=ax[0])
    # ax[0].set_title("PDP: Water Model")
    # ax[0].set_ylim([0,125])
    # for row in water_pdd.axes_:
    #     for subplot_ax in row:
    #         if subplot_ax is not None:
    #             subplot_ax.set_ylabel("PD - ml/hr")

    # energy_pdd = PartialDependenceDisplay.from_estimator(energy_model, X_test, [0, 1, 2, 3, 4],ax=ax[1])
    # ax[1].set_title("PDP: Energy Model")
    # ax[1].set_ylim([0,700])
    # for row in energy_pdd.axes_:
    #     for subplot_ax in row:
    #         if subplot_ax is not None:
    #             subplot_ax.set_ylabel("PD - W")

    # plt.show()
    # Display PDP with ICE lines (visual variance/error) for the top variables
    fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(15,6))

    # Water Model PDP + ICE (error bars added)
    # water_pdd = PartialDependenceDisplay.from_estimator(
    #     water_model, 
    #     X_test, 
    #     [0, 1, 2, 3, 4], 
    #     ax=ax[0],
    #     kind='both',         # <--- Add this
    #     centered=True,       # <--- (Optional) centers the lines for better variance comparison
    #     ice_lines_kw={"color": "tab:blue", "alpha": 0.2, "linewidth": 0.5}, # Fade the ICE lines
    #     pd_line_kw={"color": "tab:orange", "linewidth": 2}                  # Highlight the average
    # )

    # ax[0].set_title("PDP with Variance: Water Model")
    # # Note: If you use centered=True, your y-limits might need to change to show negative/relative values
    # for row in water_pdd.axes_:
    #     for subplot_ax in row:
    #         if subplot_ax is not None:
    #             subplot_ax.set_ylabel("PD - ml/hr")

    # # Energy Model PDP + ICE
    # energy_pdd = PartialDependenceDisplay.from_estimator(
    #     energy_model, 
    #     X_test, 
    #     [0, 1, 2, 3, 4], 
    #     ax=ax[1],
    #     kind='both',         # <--- Add this
    #     centered=True,       # <--- (Optional)
    #     ice_lines_kw={"color": "tab:blue", "alpha": 0.2, "linewidth": 0.5},
    #     pd_line_kw={"color": "tab:orange", "linewidth": 2}
    # )

    # ax[1].set_title("PDP with Variance: Energy Model")
    # for row in energy_pdd.axes_:
    #     for subplot_ax in row:
    #         if subplot_ax is not None:
    #             subplot_ax.set_ylabel("PD - W")

    # plt.tight_layout() # Helpful for keeping overlapping labels clean
    # plt.show()
    return water_model, energy_model

water_model,energy_model = train_model()
# save
joblib.dump(water_model, "water_model.joblib")
joblib.dump(energy_model, "energy_model.joblib")
