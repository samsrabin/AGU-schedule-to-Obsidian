# Download AGU sessions as notes for Obsidian

Given one or more URLs, makes a set of Markown files for use in Obsidian. E.g.:

<img width="978" alt="Example note or an AGU session." src="https://user-images.githubusercontent.com/10454527/207506110-68ac370a-a30f-4150-9c0c-0f06484761ae.png">


## Binary vs. Python script

I provide a pre-compiled, packaged Python binary that I have tested on my Apple Silicon Mac. It should work on other Apple Silicon Macs. Call it from a terminal like so (replacing the URL with your URL of interest):
```
$ ./agu-notes-from-url https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/168112
```
If you have some other kind of machine, you'll need to run the script using Python:
```
$ python3 agu-obsidian.py https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/168112
```
More details on the latter below.

## Instructions

In the directory where you'll be calling the binary/script (this does not have to be the directory where the binary/script is located, nor does it have to be the directory where you want the notes saved), make a text file called `settings.ini`. This should have the following content:

```
[outdir]
path = /path/to/where/you/want/files/downloaded

[thisyear]
year = 2022
```

- `outdir` `path` will be where all the notes get saved; this can be a relative or an absolute path (I think).
- `thisyear` `year` is the year of AGU you're saving notes for.

### If not using the binary
Running the script with Python requires that your Python have the following non-standard modules installed:
- `regex`
- `selenium`
If you get a `ModuleNotFoundError` for either of those, you can install them like so:
```
python3 -m pip install regex
```

You'll also need to point to a [chromedriver binary](https://chromedriver.chromium.org/downloads). The default location is at `driver/chromedriver` in the directory where the script is being called. To point somewhere else, add its path to `settings.ini` like so:
```
[chromedriver]
path = /path/to/chromedriver
```