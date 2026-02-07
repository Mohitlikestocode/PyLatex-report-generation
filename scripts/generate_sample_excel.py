import pandas as pd
import numpy as np

# Small sample of precomputed SFD/BMD for testing
X = np.linspace(0, 10, 101)
Shear = np.linspace(5, -5, 101)  # linear shear sample
Moment = 5*X - 0.25*X**2        # simple polynomial moment sample

df = pd.DataFrame({
    'X': X,
    'Shear force': Shear,
    'Bending Moment': Moment,
})

df.to_excel('data/forces.xlsx', index=False)
print('Wrote data/forces.xlsx with sample precomputed SFD/BMD')
