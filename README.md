# AGU-schedule-to-Obsidian

Given one or more URLs, `agu-notes-from-url` makes a set of Markown files for use in Obsidian. E.g.:

<img width="978" alt="Example note or an AGU session." src="https://user-images.githubusercontent.com/10454527/207506110-68ac370a-a30f-4150-9c0c-0f06484761ae.png">

In the directory where you'll be calling `agu-notes-from-url` (this does not have to be the directory where `agu-notes-from-url` is located, nor does it have to be the directory where you want the notes saved), make a text file called `settings.ini`. This should have the following content:

```
[outdir]
path = archive/test

[thisyear]
year = 2022
```

- `outdir` `path` will be where all the notes get saved; this can be a relative or an absolute path (I think).
- `thisyear` `year` is the year of AGU you're saving notes for.

If not using the binary, you'll need to point to a [chromedriver binary](https://chromedriver.chromium.org/downloads). The default location is at `driver/chromedriver` in the directory where the script is being called. To point somewhere else, add its path to `settings.ini` like so:
```
[chromedriver]
path = /path/to/chromedriver
```

Usage example (you can add more URLs after the first one):
```
$ ./agu-notes-from-url https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/168112
Importing session: Renewable Energy: Wind, Solar, Marine, Hydrokinetic, and Integration I Oral
Importing presentation: Bulk estimation and characterisation of the Turbulent Kinetic Energy induced by the sea state, Method and Results.
Importing presentation: Development of a Framework for Laboratory Testing of Hydrokinetic Microturbines to Optimize Deployment in the Field.
Importing presentation: Optimized Wave Resource Assessment and an Approach to Mitigate Wind and Wave Energy Variability: Based on the Climatology of Wind–Wave Interaction
Importing presentation: Mesoscale Modeling Sensitivity to Sea Surface Temperature Inputs in the Mid-Atlantic
Importing presentation: Offshore Wind Energy Atlas for the United States Accounting for Technical, Economic, Climate, and Metocean Restrictions
Importing presentation: Integrating Unique Observations and Models to Improve Offshore Wind Resource Assessment and Energy Production Forecasts
Importing presentation: An Analysis Effectiveness of South Korea’s Reneable Energy Policy based on the EIA Projects for Solar Power Development
Importing presentation: Long-term Global Solar Irradiance and Components as Provided and Utilized through the POWER Web Services Suite

$ tree archive
archive
└── test
    ├── GC15E-01 Bulk estimation and characterisation of the Turbulent Kinetic Energy induced by the sea state, Method and Results..md
    ├── GC15E-02 Development of a Framework for Laboratory Testing of Hydrokinetic Microturbines to Optimize Deployment in the Field..md
    ├── GC15E-03 Optimized Wave Resource Assessment and an Approach to Mitigate Wind and Wave Energy Variability—Based on the Climatology of Wind–Wave Interaction.md
    ├── GC15E-04 Mesoscale Modeling Sensitivity to Sea Surface Temperature Inputs in the Mid-Atlantic.md
    ├── GC15E-05 Offshore Wind Energy Atlas for the United States Accounting for Technical, Economic, Climate, and Metocean Restrictions.md
    ├── GC15E-06 Integrating Unique Observations and Models to Improve Offshore Wind Resource Assessment and Energy Production Forecasts.md
    ├── GC15E-07 An Analysis Effectiveness of South Korea’s Reneable Energy Policy based on the EIA Projects for Solar Power Development.md
    ├── GC15E-08 Long-term Global Solar Irradiance and Components as Provided and Utilized through the POWER Web Services Suite.md
    └── _GC15E Renewable Energy—Wind, Solar, Marine, Hydrokinetic, and Integration I Oral.md

1 directory, 9 files
```
