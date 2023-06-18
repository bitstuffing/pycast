# pycast

![pycast logo](https://raw.githubusercontent.com/bitstuffing/pycast/master/logo.png)

pycast is an independent implementation of the Chromecast protocol for Linux, built entirely in Python 3. This project aims to provide a reliable and efficient solution for screen sharing with Chromecast devices on Linux systems, without relying on existing libraries such as pychromecast.

## Motivation

The motivation behind pycast stems from the challenges encountered while using pychromecast. Although pychromecast is an impressive project, it has faced issues in delivering consistent performance. These recurring problems have inspired the development of pycast as a reliable alternative.

## Features

- **Chromecast Protocol Implementation**: pycast replicates the complete Chromecast protocol in Python, allowing seamless communication with Chromecast devices.
- **Screen Sharing**: With pycast, the final intention is you're able to easily get functions like share your local screen on a Chromecast device, enabling a rich multimedia experience, but it's not defined at this moment because this project is an investigation.
- **Independent Solution**: By building pycast without relying on external libraries, it provides a self-contained implementation for greater control and stability.

## Current Status

Currently, pycast is capable of detecting Chromecast devices and establishing communication with them. It can open a media player and stream videos successfully. However, it is important to note that Google does not provide official documentation for this protocol, making the development process more challenging.

## Installation

To install, simply run the following command:

```
pip install -r requirements.txt
```

## Usage

Here's a basic example of how to use pycast:

```python
import pycast
...
if __name__ == '__main__':
    search_device()
    for chromecast in chromecasts:
        status = go_chromecast(chromecast)  
        print(f"Status for {chromecast['friendlyName']} in ip {chromecast['ip']}: {status}")
        break
```

Simply is better, but in the future you will get more options availables. Rememer, it's an investigation project.

## Author and License

pycast is developed with love by [@bitstuffing](https://github.com/bitstuffing) and is released under the GNU General Public License v3.0. This means that you are free to use, modify, and distribute pycast, but any derivative work must also be licensed under the GPL-3.0 license, for the community, not for business use.