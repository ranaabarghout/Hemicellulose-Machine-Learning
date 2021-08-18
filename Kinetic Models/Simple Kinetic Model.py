#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from pyomo.environ import *
from pyomo.dae import *
import math
import pandas as pd 
from sklearn.model_selection import train_test_split
import csv
import numpy as np
from sklearn import metrics
import matplotlib.pyplot as plt 

# Defining Euler Time Discretization
N_sample =  len(Time_meas)
Sample = range(N_sample)
N_Time = 20                        # Of time steps
dt =  [t/N_Time for t in Time_meas] # step

N_sample_test =  len(Time_test)
Sample_test = range(N_sample_test)
N_Time_test = 20                        # Of time steps
dt_test =  [t/N_Time_test for t in Time_test] # step


# Conditions for Temperatures higher than 450 K    
for i in range(len(Tem_meas)):
    #print(Tem_meas[i])
    if Tem_meas[i]>450:
        Tem_meas[i]=450
    if Tem_meas[i] == 0:
        print('There are 0 K temperatures')

for i in range(len(Tem_test)):
    #print(Tem_meas[i])
    if Tem_test[i]>450:
        Tem_test[i]=450
    if Tem_test[i] == 0:
        print('There are 0 K temperatures')    

# Converting acid concentration (proton)         
for i in range(len(CA_meas)):
    CAweight_meas[i]=CA_meas[i]*98.079/2/10
      
for i in range(len(CA_test)):
    CAweight_test[i]=CA_test[i]*98.079/2/10

# Defining Euler time discretization
Time = range(N_Time)                    
Time_ = range(N_Time-1) 
print(Time_)
Time_test2 = range(N_Time_test)                    
Time__test = range(N_Time_test-1) 
print(Time__test)

# Pyomo model variables 
model = ConcreteModel()
model.logAh = Var(within=PositiveReals, bounds=(20, 70), initialize = 32)  #1,8e14
model.logAd = Var(within=PositiveReals, bounds=(20, 70), initialize = 32)  #1.4e14
model.Eh = Var(within=PositiveReals, bounds=(100, 1e8), initialize = 1e5)     #1.4e5
model.Ed = Var(within=PositiveReals, bounds=(100, 1e8), initialize = 1e5)     #1.4e5

model.logAh_CA = Var(within=PositiveReals, bounds=(20, 70), initialize = 32)  #1,8e14
model.logAd_CA = Var(within=PositiveReals, bounds=(20, 70), initialize = 32)  #1.4e14
model.Eh_CA = Var(within=PositiveReals, bounds=(100, 1e8), initialize = 1e5)     #1.4e5
model.Ed_CA = Var(within=PositiveReals, bounds=(100, 1e8), initialize = 1e5)     #1.4e5   
model.mh_CA = Var(within=PositiveReals, bounds=(0.1,3.8), initialize = 1)         #5.5
model.md_CA = Var(within=PositiveReals, bounds=(0.1,3.8), initialize = 1)         #1.3 

model.kh = Var(Sample, within=PositiveReals,bounds=(1e-10,1000000), initialize=1)         #1e-9
model.kd = Var(Sample, within=PositiveReals,bounds=(1e-10,1000000), initialize=1)

model.H = Var(Sample, Time, within=Reals, initialize=0.5)
model.X = Var(Sample, Time, within=Reals, initialize=0.5)
model.yield_cal = Var(Sample, within=Reals, initialize=50)

model.constraints = ConstraintList()

# Arrhenius Equation Calculation
for s in Sample:
    if np.any(CA_meas[s]==0):
        model.constraints.add(log(model.kh[s]) == model.logAh - model.Eh/(R*Tem_meas[s]) )
        model.constraints.add(log(model.kd[s]) == model.logAd - model.Ed/(R*Tem_meas[s]) ) 
    else:
        model.constraints.add(log(model.kh[s]) == model.logAh_CA + model.mh_CA*log(CAweight_meas[s]) - model.Eh_CA/(R*Tem_meas[s]) )
        model.constraints.add(log(model.kd[s]) == model.logAd_CA + model.md_CA*log(CAweight_meas[s]) - model.Ed_CA/(R*Tem_meas[s]) )

# Discretize Using Implicit Euler
for s in Sample:
    for t in Time_:
        model.constraints.add( model.H[s,t+1] - model.H[s,t] == -model.kh[s]*model.H[s,t+1]*dt[s] )
        model.constraints.add( model.X[s,t+1] - model.X[s,t]   == (model.kh[s]*model.H[s,t+1] - model.kd[s]*model.X[s,t+1])*dt[s]  ) 
        
#Initial Values
for s in Sample:
    model.constraints.add(model.H[s,0] == (Fx_meas[s]*rho_w/(100*(LSR_meas[s]))))
    model.constraints.add(model.X[s,0] == X0_meas[s])

    
#Yield Calculation
for s in Sample:
    model.constraints.add(model.yield_cal[s] == 100*model.X[s, N_Time-1]*LSR_meas[s]/(1000*(Fx_meas[s]/100)))
    

# Objective function
model.objective = Objective(expr = sum((model.yield_cal[s]-Yield_meas[s])**2 for s in Sample))


solver=SolverFactory('ipopt')
solver.options['max_iter'] = 10000
solver.solve(model,tee=True)

#--------------------------------------- Calculation of MAE for Test Data ---------------------------------

bestlogAh = model.logAh.value
bestlogAd = model.logAd.value
bestEh = model.Eh.value
bestEd = model.Ed.value
bestlogAh_CA = model.logAh_CA.value
bestlogAd_CA = model.logAd_CA.value
bestEh_CA = model.Eh_CA.value
bestEd_CA = model.Ed_CA.value
bestmh_CA = model.mh_CA.value
bestmd_CA = model.md_CA.value

print('logAh: ',model.logAh.value)
print('logAd: ',model.logAd.value)
print('Eh (J/mol-K): ',model.Eh.value)
print('Ed (J/mol-K): ',model.Ed.value)


print('logAh_CA: ',model.logAh_CA.value)
print('logAd_CA: ',model.logAd_CA.value)
print('Eh_CA (J/mol-K): ',model.Eh_CA.value)
print('Ed_CA (J/mol-K): ',model.Ed_CA.value)
print('mh: ',model.mh_CA.value)
print('md: ',model.md_CA.value)

# Plotting Concentration vs. Time Plots

Xvalues = np.empty(N_Time)
Hvalues = np.empty(N_Time)
Timepts  = np.linspace(0,Time_meas[6], N_Time)

for t in Time: 
    Xvalues[t] = model.X[6,t].value 
    Hvalues[t] = model.H[6,t].value
    
plt.plot(Timepts,Xvalues, linestyle='-', label='Xylose Concentration')
plt.plot(Timepts, Hvalues, linestyle='--', label='Hemicellulose')
plt.legend()
plt.show()

print("Time points: ", Timepts)

print("H:  ")
for t in Time:
    print(model.H[6,t].value)   
    
print("X:  ")
for t in Time:
    print(model.X[6,t].value)



Yield_Calc = np.zeros_like(Time_meas)
print("Predicted Yield:")
# print solutions
for s in Sample:
    print(model.yield_cal[s].value)
    Yield_Calc[s] = model.yield_cal[s].value

MAE_train = metrics.mean_absolute_error(Yield_meas,Yield_Calc)
print("MAE_train: ", MAE_train)



model_test = ConcreteModel()
model_test.kf_test = Var(Sample_test, within=PositiveReals)
model_test.kd_test = Var(Sample_test, within=PositiveReals)
model_test.Hf_test = Var(Sample_test, Time_test2, within=Reals)
model_test.X_test = Var(Sample_test, Time_test2, within=Reals)
model_test.yield_cal_test = Var(Sample_test, within=Reals)

model_test.constraints = ConstraintList()
for s in Sample_test:
    if np.any(CA_test[s]==0):
        model_test.constraints.add(log(model_test.kf_test[s]) == bestlogAh - bestEh/(R*Tem_test[s]) )
        model_test.constraints.add(log(model_test.kd_test[s]) == bestlogAd - bestEd/(R*Tem_test[s]) )
    else:
        model_test.constraints.add(log(model_test.kf_test[s]) == bestlogAh_CA + bestmh_CA*log(CAweight_test[s]) - bestEh_CA/(R*Tem_test[s]) )
        model_test.constraints.add(log(model_test.kd_test[s]) == bestlogAd_CA + bestmd_CA*log(CAweight_test[s]) - bestEd_CA/(R*Tem_test[s]) )


for s in Sample_test:
    for t in Time__test:
        model_test.constraints.add((model_test.Hf_test[s,t+1] - model_test.Hf_test[s,t]) == -model_test.kf_test[s]*model_test.Hf_test[s,t+1]*dt_test[s])
        model_test.constraints.add((model_test.X_test[s,t+1] - model_test.X_test[s,t]) == (model_test.kf_test[s]*model_test.Hf_test[s,t+1] - model_test.kd_test[s]*model_test.X_test[s,t+1])*dt_test[s])
        
#Initial Values for Test Set                                                                                                                                                                          
for s in Sample_test:
    model_test.constraints.add(model_test.Hf_test[s,0] == (Fx_test[s]*rho_w/(100*(LSR_test[s]))))
    model_test.constraints.add(model_test.X_test[s,0] == X0_test[s])

#Yield Calculation for Test Set                                                                                                                                                                       
for s in Sample_test:
    model_test.constraints.add(model_test.yield_cal_test[s] == 100*model_test.X_test[s, N_Time_test-1]*LSR_test[s]/(1000*(Fx_test[s]/100)))


solver=SolverFactory('ipopt')
solver.solve(model_test,tee=True)


Yield_CalcTest = np.zeros_like(Time_test)
for s in Sample_test:
    Yield_CalcTest[s] = model_test.yield_cal_test[s].value
MAE_test = metrics.mean_absolute_error(Yield_test,Yield_CalcTest)
print("MAE_test: ", MAE_test)


# In[ ]:




