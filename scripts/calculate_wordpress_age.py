#!/usr/bin/env python3
"""Calculate age statistics for WordPress posts."""

from datetime import datetime
import statistics

# Post dates from WordPress query (top 50 posts by views)
post_dates = [
    "2026-05-17", "2026-05-16", "2026-06-07", "2026-04-26", "2026-05-25",
    "2026-04-15", "2026-04-17", "2026-05-03", "2026-06-01", "2026-04-22",
    "2026-05-25", "2026-05-09", "2026-05-21", "2026-06-14", "2026-06-12",
    "2026-05-19", "2026-05-22", "2026-05-31", "2026-06-15", "2026-06-14",
    "2026-06-16", "2026-05-22", "2026-05-02", "2026-04-13", "2026-05-12",
    "2026-05-19", "2026-06-19", "2026-06-16", "2026-04-22", "2026-04-15",
    "2026-04-13", "2026-06-14", "2026-06-17", "2026-06-15", "2026-04-22",
    "2026-06-12", "2026-06-21", "2026-04-13", "2026-04-14", "2026-05-11",
    "2026-05-19", "2026-05-09", "2026-06-30", "2026-06-14", "2026-04-22",
    "2026-04-29", "2026-04-13", "2026-06-14", "2026-05-11", "2026-06-18",
]

today = datetime(2026, 8, 23)

# Calculate age in days for each post
ages = []
for date_str in post_dates:
    post_date = datetime.strptime(date_str, "%Y-%m-%d")
    age_days = (today - post_date).days
    ages.append(age_days)

# Calculate statistics
mean_age = statistics.mean(ages)
median_age = statistics.median(ages)
min_age = min(ages)
max_age = max(ages)

# Calculate weight factor
clarity_window = 30  # days
weight_by_mean = clarity_window / mean_age
weight_by_median = clarity_window / median_age

print(f"WordPress Posts Age Analysis (n=50)")
print(f"=" * 50)
print(f"Reference date: {today.strftime('%Y-%m-%d')}")
print(f"")
print(f"Age Statistics (days):")
print(f"  Mean:   {mean_age:.1f} days")
print(f"  Median: {median_age:.1f} days")
print(f"  Min:    {min_age} days (newest post)")
print(f"  Max:    {max_age} days (oldest post)")
print(f"")
print(f"Weight Calculation:")
print(f"  Clarity window: {clarity_window} days")
print(f"  ")
print(f"  By mean:   {clarity_window} / {mean_age:.1f} = {weight_by_mean:.4f}")
print(f"  By median: {clarity_window} / {median_age:.1f} = {weight_by_median:.4f}")
print(f"")
print(f"Recommended weight (using mean): {weight_by_mean:.4f}")
print(f"Rounded for readability:         {round(weight_by_mean, 2)}")
