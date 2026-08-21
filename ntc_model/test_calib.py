import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
import traceback

X = np.random.rand(100, 5)
y = np.random.randint(0, 2, 100)
m = LogisticRegression().fit(X, y)

print("Trying cv='prefit'")
try:
    c = CalibratedClassifierCV(estimator=m, cv="prefit")
    c.fit(X, y)
    print("SUCCESS cv='prefit'")
except Exception as e:
    print(repr(e))

print("Trying ensemble=False, cv=None")
try:
    c = CalibratedClassifierCV(estimator=m, ensemble=False, cv=None)
    c.fit(X, y)
    print("SUCCESS ensemble=False, cv=None")
except Exception as e:
    print(repr(e))
