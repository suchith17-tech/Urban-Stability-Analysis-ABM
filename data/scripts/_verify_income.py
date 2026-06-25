import pandas as pd
import numpy as np

df = pd.read_csv(r'data/processed/income_distribution.csv')

print("KEY VERIFICATION TESTS:")
print()

# Test 1: Sigmas differ across groups
g_sigmas = df.groupby('income_group')['lognorm_sigma'].first()
print("Test 1: Sigma per group")
for g, s in g_sigmas.items():
    print(f"  {g:14s}: sigma={s:.3f}")
print()

# Test 2: Inter-city inequality
print("Test 2: Annual income mean by city and group")
for g in ['extreme_poor', 'bpl_poor', 'non_poor']:
    sub = df[df['income_group']==g][['city','annual_income_mean']].sort_values('annual_income_mean', ascending=False)
    print(f"  {g}:")
    for _, r in sub.iterrows():
        print(f"    {r['city']:20s}: Rs {int(r['annual_income_mean']):>8,}")
print()

# Test 3: Intra-group spread P10/P90
print("Test 3: Intra-group spread (P10 vs P90)")
for city in ['Bengaluru', 'Belagavi']:
    for g in ['bpl_poor', 'non_poor']:
        row = df[(df['city']==city) & (df['income_group']==g)].iloc[0]
        samples = np.exp(np.random.normal(row['lognorm_mean'], row['lognorm_sigma'], 10000))
        p10 = np.percentile(samples, 10)
        p90 = np.percentile(samples, 90)
        print(f"  {city} {g}: P10=Rs {int(p10):>7,}, P90=Rs {int(p90):>7,}, ratio={p90/p10:.1f}x")
