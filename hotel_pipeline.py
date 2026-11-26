
import matplotlib
matplotlib.use("Agg")  # save charts to files, no window
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RAW = "data/raw/"
OUT = "output/"
FIG = "figures/"

# One colour per hotel, used in every chart
CITY, RESORT, GREY = "#2b5fd9", "#e8742a", "#b5b5b0"
COLORS = {"City Hotel": CITY, "Resort Hotel": RESORT}
plt.rcParams.update({
    "font.family": ["Helvetica Neue", "DejaVu Sans"], "font.size": 14,
    "axes.titlesize": 17, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#888888", "axes.grid": True, "axes.axisbelow": True, "axes.grid.axis": "y",
    "grid.color": "#e6e6e6", "legend.frameon": False,
})

log = []

def report(table, step, rows_before, rows_after, values_changed):
    log.append([table, step, rows_before, rows_after, int(values_changed)])
    print(f"  [{table}] {step}: rows {rows_before} -> {rows_after}, values changed: {values_changed}")

# LOAD
print("\n1. LOAD")

pms_raw = pd.read_excel(RAW + "hotel_reservations_pms.xlsx", sheet_name="bookings", dtype=str)
crm_raw = pd.read_csv(RAW + "hotel_bookings_crm.csv", sep=";", dtype=str)
print("PMS:", pms_raw.shape, " CRM:", crm_raw.shape)

# Columns that mean the same thing
#   booking_id  = BookingRef
#   hotel       = property
#   arrival_date_year/month/day = checkin_date
#   adults      = n_adults
#   is_canceled = reservation_status
#   adr x nights = total_price


# DESCRIBE
print("\n2. DESCRIBE")

print("\nMissing values (PMS):\n", pms_raw.isna().sum()[pms_raw.isna().sum() > 0])
print("\nMissing values (CRM):\n", crm_raw.isna().sum()[crm_raw.isna().sum() > 0])

print("\nDuplicates")
print("  PMS exact copies:", pms_raw.duplicated().sum())
print("  PMS booking_id repeated:", pms_raw["booking_id"].duplicated().sum())
print("  CRM exact copies:", crm_raw.duplicated().sum())

print("\nInconsistent spellings (number of different values)")
print("  hotel:", pms_raw["hotel"].nunique(), "for 2 hotels")
print("  property:", crm_raw["property"].nunique(), "for 2 hotels")
print("  market_segment:", crm_raw["market_segment"].nunique(), "for 8 segments")
print("  reservation_status:", crm_raw["reservation_status"].nunique(), "for 3 statuses")
print("  arrival_date_month:", pms_raw["arrival_date_month"].nunique(), "for 12 months")

adr_raw = pd.to_numeric(pms_raw["adr"], errors="coerce")
print("\nInaccurate values")
print("  adr that is not a number:", (adr_raw.isna() & pms_raw["adr"].notna()).sum())
print("  adr < 0:", (adr_raw < 0).sum(), "| adr > 1000 EUR per night:", (adr_raw > 1000).sum())
print("  adults > 10 in one room:", (pd.to_numeric(pms_raw["adults"]) > 10).sum())
print("  stays_in_week_nights = -1:", (pms_raw["stays_in_week_nights"] == "-1").sum())
print("  lead_time_days = 9999:", (crm_raw["lead_time_days"] == "9999").sum())


# CLEAN PMS
print("\n3a. CLEAN PMS")
pms = pms_raw.copy()

n = len(pms)
pms = pms.drop_duplicates()
report("PMS", "drop exact duplicates", n, len(pms), n - len(pms))

n = len(pms)
pms = pms.sort_values("record_updated_at").drop_duplicates(subset="booking_id", keep="last")
report("PMS", "keep latest version of each booking", n, len(pms), n - len(pms))

old = pms["hotel"]
pms["hotel"] = pms["hotel"].str.strip().str.lower().replace(
    {"city hotel": "City Hotel", "resort hotel": "Resort Hotel"})
report("PMS", "hotel: strip + lower -> 2 names", len(pms), len(pms), (old != pms["hotel"]).sum())

old = pms["is_canceled"]
pms["is_canceled"] = pd.to_numeric(pms["is_canceled"].replace({"no": "0", "yes": "1"}))
report("PMS", "is_canceled: no/yes -> 0/1", len(pms), len(pms), old.isin(["no", "yes"]).sum())

pms["deposit_type"] = pms["deposit_type"].str.strip()  #clean deposit type

MONTHS = {"jan": "1", "feb": "2", "mar": "3", "apr": "4", "may": "5", "jun": "6",
          "jul": "7", "aug": "8", "sep": "9", "oct": "10", "nov": "11", "dec": "12"}
old = pms["arrival_date_month"]
pms["arrival_month"] = pd.to_numeric(pms["arrival_date_month"].str.lower().str[:3].replace(MONTHS))
report("PMS", "arrival month: name/abbreviation/number -> 1-12", len(pms), len(pms),
       (old.str.len() <= 3).sum())
pms["arrival_year"] = pd.to_numeric(pms["arrival_date_year"])

for col in ["stays_in_weekend_nights", "stays_in_week_nights", "adults", "children",
            "babies", "booking_changes", "total_of_special_requests"]:
    pms[col] = pd.to_numeric(pms[col])

old = pms["adr"]
adr_text = pms["adr"].str.strip(" €EUR").str.replace(",", ".")
pms["adr"] = pd.to_numeric(adr_text, errors="coerce") #becomes NaN
report("PMS", "adr: text -> number (placeholders -> NaN)", len(pms), len(pms),
       (pd.to_numeric(old, errors="coerce").isna()).sum())

negative = (pms["adr"] < 0).sum()
pms["adr"] = pms["adr"].abs()
report("PMS", "adr < 0 -> abs()", len(pms), len(pms), negative)

minus_one = (pms["stays_in_week_nights"] < 0).sum() #how many -1 nights
pms["stays_in_week_nights"] = pms["stays_in_week_nights"].mask(pms["stays_in_week_nights"] < 0)
report("PMS", "week nights -1 -> NaN", len(pms), len(pms), minus_one)

filled = pms["children"].isna().sum()
pms["children"] = pms["children"].fillna(0) #fill NaN with 0
report("PMS", "children NaN -> 0", len(pms), len(pms), filled)

filled = pms["meal"].isna().sum()
pms["meal"] = pms["meal"].fillna("Undefined")
report("PMS", "meal NaN -> 'Undefined'", len(pms), len(pms), filled)


# CLEAN CRM
print("\n3b. CLEAN CRM")
crm = crm_raw.copy()

n = len(crm)
crm = crm.dropna(how="all")
report("CRM", "drop empty rows", n, len(crm), n - len(crm))
n = len(crm)
crm = crm.drop_duplicates()
report("CRM", "drop exact duplicates", n, len(crm), n - len(crm))

crm["booking_id"] = crm["BookingRef"] #same key name than PMS

crm["property"] = crm["property"].str.strip().str.lower().replace(
    {"city hotel": "City Hotel", "resort hotel": "Resort Hotel"})

SEGMENTS = {"online ta": "Online TA", "online t.a.": "Online TA", "onlne ta": "Online TA",
            "offline ta/to": "Offline TA/TO", "offline ta-to": "Offline TA/TO",
            "ofline ta/to": "Offline TA/TO", "groups": "Groups", "group": "Groups",
            "direct": "Direct", "corporate": "Corporate", "corporte": "Corporate",
            "complementary": "Complementary", "aviation": "Aviation", "undefined": "Undefined"}
old = crm["market_segment"]
crm["market_segment"] = crm["market_segment"].str.strip().str.lower().replace(SEGMENTS)
report("CRM", "market_segment: 22 spellings -> 8", len(crm), len(crm),
       (old != crm["market_segment"]).sum())
print("  segments now:", crm["market_segment"].nunique())

STATUS = {"check-out": "Check-Out", "checkout": "Check-Out", "check out": "Check-Out",
          "canceled": "Canceled", "cancelled": "Canceled",
          "no-show": "No-Show", "no show": "No-Show"}
old = crm["reservation_status"]
crm["reservation_status"] = crm["reservation_status"].str.strip().str.lower().replace(STATUS)
report("CRM", "reservation_status: 11 spellings -> 3", len(crm), len(crm),
       (old != crm["reservation_status"]).sum())

crm["guest_country"] = (crm["guest_country"].str.strip().str.upper()
                        .replace({"PT": "PRT", "PORTUGAL": "PRT", "CN": "CHN",
                                  "UNKNOWN": "Unknown", "-": "Unknown"})
                        .fillna("Unknown"))

d = crm["checkin_date"]
crm["checkin_date"] = (pd.to_datetime(d, format="%Y-%m-%d", errors="coerce")       # 2016-12-03
                       .fillna(pd.to_datetime(d, format="%d %b %Y", errors="coerce"))   # 13 Apr 2017
                       .fillna(pd.to_datetime(d, format="%d/%m/%Y", errors="coerce")))  # 12/09/2015
print("  checkin_date not read:", crm["checkin_date"].isna().sum())

crm["lead_time_days"] = pd.to_numeric(crm["lead_time_days"].str.replace(" days", ""))
placeholder = (crm["lead_time_days"] == 9999).sum()
crm["lead_time_days"] = crm["lead_time_days"].mask(crm["lead_time_days"] == 9999)
report("CRM", "lead_time 9999 -> NaN", len(crm), len(crm), placeholder)

crm["total_price"] = pd.to_numeric(crm["total_price"].str.replace(",", "."))
crm["n_adults"] = pd.to_numeric(crm["n_adults"])
crm["is_repeated_guest"] = pd.to_numeric(crm["is_repeated_guest"])

crm = crm.drop(columns=["company_id", "BookingRef"]) #drop company_id, most empty


# MERGE
print("\n4. MERGE")
in_both = pms["booking_id"].isin(crm["booking_id"]).sum()
print("  in both files:", in_both,
      "| PMS only:", len(pms) - in_both,
      "| CRM only:", len(crm) - in_both)

df = pd.merge(pms, crm, on="booking_id", how="outer") #outer join to keep all records
report("MERGED", "outer merge on booking_id", len(pms) + len(crm), len(df), 0)
print("  booking_id repeated after merge:", df["booking_id"].duplicated().sum())


# FILL
print("\n5. FILL WITH THE OTHER FILE")

df["hotel"] = df["hotel"].fillna(df["property"])
df["arrival_month"] = df["arrival_month"].fillna(df["checkin_date"].dt.month)
df["arrival_year"] = df["arrival_year"].fillna(df["checkin_date"].dt.year) #fill columns from PMS

typo = (df["adults"] > 10) & (df["n_adults"] <= 10)
df["adults"] = df["adults"].where(~typo, df["n_adults"])
df["adults"] = df["adults"].fillna(df["n_adults"]).fillna(df["adults"].mode()[0]) #2x fillna as security
report("MERGED", "adults > 10 -> CRM n_adults", len(df), len(df), typo.sum())

crm_canceled = pd.to_numeric(df["reservation_status"].replace({"Check-Out": "0", "Canceled": "1", "No-Show": "1"}))
conflicts = (crm_canceled - df["is_canceled"]).abs() == 1
df["is_canceled"] = crm_canceled.fillna(df["is_canceled"])
report("MERGED", "is_canceled from CRM status", len(df), len(df), conflicts.sum())

nights = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]
confirmed = (df["adr"] * nights - df["total_price"]).abs() < 1 #check good prices
x100 = (df["adr"] > 1000) & ~confirmed
df["adr"] = df["adr"].where(~x100, df["adr"] / 100) #divide bad prices
report("MERGED", "adr x100 -> / 100 (checked with CRM total_price)", len(df), len(df), x100.sum())


filled = df["stays_in_week_nights"].isna() & df["adr"].notna()
deduced = (df["total_price"] / df["adr"]).round() - df["stays_in_weekend_nights"] #deduce from total and daily prices
df["stays_in_week_nights"] = df["stays_in_week_nights"].fillna(deduced.mask(deduced < 0)) #fillna and mask to use deduced column
median_by_hotel = df.groupby("hotel")["stays_in_week_nights"].transform("median")
df["stays_in_week_nights"] = df["stays_in_week_nights"].fillna(median_by_hotel) #fill unknown values by median
report("MERGED", "week nights = total_price / adr - weekend", len(df), len(df), filled.sum())
df["nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]

missing_adr = df["adr"].isna().sum()
df["adr"] = df["adr"].fillna(df["total_price"] / df["nights"]) #total / nights = daily rate
report("MERGED", "adr NaN = total_price / nights", len(df), len(df), missing_adr - df["adr"].isna().sum())

missing_total = df["total_price"].isna().sum()
df["total_price"] = df["total_price"].fillna(df["adr"] * df["nights"]) #daily rate * nights = total
report("MERGED", "total_price NaN = adr x nights", len(df), len(df), missing_total - df["total_price"].isna().sum())

missing_lead = df["lead_time_days"].isna() & df["market_segment"].notna()
df["lead_time_days"] = df["lead_time_days"].fillna(df.groupby("hotel")["lead_time_days"].transform("median")) #replace by median of same hotel
report("MERGED", "lead_time NaN -> median by hotel", len(df), len(df), missing_lead.sum())

for col in ["market_segment", "distribution_channel", "customer_type", "deposit_type", "meal"]:
    df[col] = df[col].fillna("Unknown")

df["adr_outlier"] = False
for hotel in ["City Hotel", "Resort Hotel"]:
    rows = df["hotel"] == hotel
    q1 = df.loc[rows, "adr"].quantile(0.25)
    q3 = df.loc[rows, "adr"].quantile(0.75)
    iqr = q3 - q1
    outside = ~df["adr"].between(q1 - 1.5 * iqr, q3 + 1.5 * iqr) & df["adr"].notna() #outliers
    df.loc[rows, "adr_outlier"] = outside[rows]
report("MERGED", "flag adr outliers (IQR per hotel), kept", len(df), len(df), df["adr_outlier"].sum())

df["revenue"] = df["total_price"].where(df["is_canceled"] == 0, 0)


# EXPORT
print("\n6. EXPORT")
clean = df.drop(columns=["property", "n_adults", "checkin_date", "arrival_date_year",
                        "arrival_date_month", "arrival_date_day_of_month"]) #remove dup columns
clean.to_csv(OUT + "hotel_bookings_clean.csv", index=False)
pd.DataFrame(log, columns=["table", "step", "rows_before", "rows_after", "values_changed"]) \
    .to_csv(OUT + "cleaning_log.csv", index=False)
print("  clean table:", clean.shape, "| cleaning steps:", len(log))
print("  missing values left:\n", clean.isna().sum()[clean.isna().sum() > 0])


# CHARTS: BEFORE / AFTER CLEANING
print("\n7a. CHARTS before / after")

#hotel names
fig, axes = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={"width_ratios": [1.6, 1]})
raw_counts = pms_raw["hotel"].value_counts().sort_values()
axes[0].barh(raw_counts.index.str.replace(" ", "·"), raw_counts.values, color=GREY)
axes[0].set_title(f"Before: {len(raw_counts)} hotel names")
axes[0].set_xscale("log")
axes[0].set_xlabel("bookings (log scale)   · = a space")
clean_counts = pms["hotel"].value_counts().sort_values()
axes[1].barh(clean_counts.index, clean_counts.values, color=[COLORS[h] for h in clean_counts.index])
for i, v in enumerate(clean_counts.values):
    axes[1].text(v, i, f" {v:,}", va="center")
axes[1].set_title("After: 2 hotels")
axes[1].set_xlim(0, clean_counts.max() * 1.3)
axes[1].set_xlabel("bookings")
for ax in axes:
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
fig.tight_layout()
fig.savefig(FIG + "01_hotel_names_before_after.png", dpi=150)
plt.close(fig)

#prices per night
fig, axes = plt.subplots(1, 2, figsize=(13, 6.2), sharey=True)
axes[0].scatter(range(len(adr_raw)), adr_raw, s=4, color=GREY)
axes[0].set_title(f"Before: from {adr_raw.min():,.0f} to {adr_raw.max():,.0f} EUR")
axes[0].set_ylabel("price per night (EUR)")
axes[1].scatter(range(len(df)), df["adr"], s=4, c=df["hotel"].replace(COLORS))
axes[1].set_title(f"After: from {df['adr'].min():,.0f} to {df['adr'].max():,.0f} EUR")
for ax in axes:
    ax.set_xlabel("booking (row order)")
    ax.set_xticks([])
fig.tight_layout()
fig.savefig(FIG + "02_price_before_after.png", dpi=150)
plt.close(fig)


# WHICH HOTEL PERFORMS BEST?
print("\n7b. WHICH HOTEL PERFORMS BEST?")
stayed = df[df["is_canceled"] == 0]

scoreboard = df.groupby("hotel").agg(
    bookings=("booking_id", "count"),
    cancel_rate=("is_canceled", "mean"),
    revenue=("revenue", "sum"),
)
scoreboard["stays"] = stayed.groupby("hotel")["booking_id"].count()
scoreboard["median_adr"] = stayed.groupby("hotel")["adr"].median()
scoreboard["avg_nights"] = stayed.groupby("hotel")["nights"].mean()
scoreboard["revenue_per_stay"] = scoreboard["revenue"] / scoreboard["stays"]
scoreboard["revenue_per_booking"] = scoreboard["revenue"] / scoreboard["bookings"]
scoreboard["repeat_guests"] = stayed.groupby("hotel")["is_repeated_guest"].mean()
scoreboard["lost_revenue"] = df[df["is_canceled"] == 1].groupby("hotel")["total_price"].sum()
print(scoreboard.T.round(2).to_string())
scoreboard.T.round(3).to_csv(OUT + "scoreboard.csv") #global scoreboard of hotels

#Bookings made vs stays
fig, ax = plt.subplots(figsize=(13, 4.4))
hotels = scoreboard.index
ax.barh(hotels, scoreboard["stays"], color=[COLORS[h] for h in hotels], height=0.55, label="stayed")
ax.barh(hotels, scoreboard["bookings"] - scoreboard["stays"], left=scoreboard["stays"],
        color=GREY, height=0.55, label="cancelled")
for i, h in enumerate(hotels):
    ax.text(scoreboard.loc[h, "stays"] / 2, i, f"{scoreboard.loc[h, 'stays']:,} stayed",
            ha="center", va="center", color="white", fontweight="bold")
    ax.text(scoreboard.loc[h, "bookings"], i,
            f"  {scoreboard.loc[h, 'cancel_rate']:.0%} cancelled", va="center")
ax.set_xlim(0, scoreboard["bookings"].max() * 1.22)
ax.set_xlabel("bookings")
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.set_title("City Hotel sells twice as much, but loses 4 bookings in 10")
fig.tight_layout()
fig.savefig(FIG + "03_bookings_vs_stays.png", dpi=150)
plt.close(fig)

#Price per night by month (stays only)
season = pd.pivot_table(stayed, values="adr", index="arrival_month", columns="hotel",
                        aggfunc="median")
fig, ax = plt.subplots(figsize=(13, 5))
for hotel in season.columns:
    ax.plot(season.index, season[hotel], marker="o", lw=2.5, color=COLORS[hotel])
    ax.text(12.2, season.loc[12, hotel], hotel, color=COLORS[hotel], va="center", fontweight="bold")
ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                             "Oct", "Nov", "Dec"])
ax.set_xlim(0.6, 13.6)
ax.set_ylabel("median price per night (EUR)")
ax.set_title("The Resort charges more in summer, the City is steady all year")
fig.tight_layout()
fig.savefig(FIG + "04_price_by_month.png", dpi=150)
plt.close(fig)

#Revenue per month, 2016 only (only complete year)
year_2016 = stayed[stayed["arrival_year"] == 2016]
monthly = pd.pivot_table(year_2016, values="revenue", index="arrival_month", columns="hotel",
                         aggfunc="sum") / 1000
fig, ax = plt.subplots(figsize=(13, 5))
width = 0.4
ax.bar(monthly.index - width / 2, monthly["City Hotel"], width, color=CITY, label="City Hotel")
ax.bar(monthly.index + width / 2, monthly["Resort Hotel"], width, color=RESORT, label="Resort Hotel")
ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                             "Oct", "Nov", "Dec"])
ax.set_ylabel("revenue (k EUR)")
ax.legend(loc="upper left")
ax.set_title("2016 revenue: the City leads 11 months, the Resort wins August")
fig.tight_layout()
fig.savefig(FIG + "05_revenue_by_month_2016.png", dpi=150)
plt.close(fig)

#Where cancellation comes from in %
main_segments = ["Online TA", "Offline TA/TO", "Groups", "Direct", "Corporate"]
rate = pd.pivot_table(df[df["market_segment"].isin(main_segments)], values="is_canceled",
                      index="hotel", columns="market_segment", aggfunc="mean")[main_segments]
fig, ax = plt.subplots(figsize=(13, 3.8))
sns.heatmap(rate * 100, annot=True, fmt=".0f", cmap="Greys", vmin=0, vmax=100, cbar=False,
            linewidths=2, linecolor="white", annot_kws={"size": 18}, ax=ax)
ax.set_xlabel("")
ax.set_ylabel("")
ax.tick_params(axis="y", rotation=0)
ax.grid(False)
ax.set_title("% cancelled: the City cancels more in every segment")
fig.tight_layout()
fig.savefig(FIG + "06_cancel_by_segment.png", dpi=150)
plt.close(fig)

#Cheaper nights but longer stays
panels = [("median_adr", "Price per night", "{:.0f} EUR"),
          ("avg_nights", "Nights per stay", "{:.1f}"),
          ("revenue_per_stay", "Revenue per stay", "{:.0f} EUR")]
fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
for ax, (col, title, fmt) in zip(axes, panels):
    ax.bar(hotels, scoreboard[col], color=[COLORS[h] for h in hotels], width=0.6)
    for i, v in enumerate(scoreboard[col]):
        ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontweight="bold")
    ax.set_title(title, loc="center", fontsize=15)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_ylim(0, scoreboard[col].max() * 1.2)
fig.suptitle("A Resort night is cheaper, but guests stay longer: each stay earns more",
             x=0.01, ha="left", fontsize=17, fontweight="bold")
fig.tight_layout()
fig.savefig(FIG + "07_value_of_a_stay.png", dpi=150)
plt.close(fig)

print("\nDone: output/ and figures/")
