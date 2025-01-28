# Home Assistant integration for BenQ projectors

![Python][python-shield]
[![GitHub Release][releases-shield]][releases]
[![Licence][license-shield]][license]
[![Maintainer][maintainer-shield]][maintainer]
[![Home Assistant][homeassistant-shield]][homeassistant]
[![HACS][hacs-shield]][hacs]  
[![Github Sponsors][github-shield]][github]
[![PayPal][paypal-shield]][paypal]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Patreon][patreon-shield]][patreon]

## Introduction

Home Assistant integration to control BenQ projectors over the serial or network interface
including serial to network bridges like [esp-link](https://github.com/jeelabs/esp-link).

<img src="https://raw.githubusercontent.com/rrooggiieerr/homeassistant-benqprojector/main/Screenshot%201b.png" style="width: 50%;"/>

## Features

* Connects to a BenQ projector over serial or network interface
* Sending commands to projectors
* Reading the projector status
* Uses asynchronous IO

## Protocol

BenQ projectors and flat panels with a serial port can support one of three protocols. This
integration supports projectors which are of the L, P, T, W and X series but probably also others.

This integration works if your projector supports the following command structure:

```
<CR>*<key>=<value>#<CR>
```

Where `<CR>` is a Carriage Return

Examples:  
Power on   : `<CR>*pow=on#<CR>`  
Power off  : `<CR>*pow=off#<CR>`  
Change source to HDMI: `<CR>*sour=hdmi#<CR>`  

### PJLink

This integration does **not** implement the PJLink protocol, but a proparitary BenQ protocol
instead. The PJLink protocol is covered by it's own [PJLink integration](https://www.home-assistant.io/integrations/pjlink/).

## Hardware

### Serial port

I'm using a generic serial to USB converter to connect to my projector. The projector has a male
DB9 connector, thus you need a female conector on your USB converter.

You can lookup and change the baud rate in the menu of your BenQ projector.

### Network connected projectors

The commands as described above also work over a network connection. Although I don't own such
projector I have implemented the network functionality using a serial to WiFi bridge. The network
support for integrated networked BenQ projectors is thus experimental. Let me know if your network
connected BenQ projector works.

Example of a serial to WiFi bridge using a serial to TTL converter and a Wemos C3 Mini:

<img src="https://raw.githubusercontent.com/rrooggiieerr/homeassistant-benqprojector/main/serial%20to%20network%20bridge.png" style="width: 25%;"/>

It has to be said that a direct serial connection to the projector is much more responsive than
using a serial to WiFi bridge. Maybe this is different on an integrated networked BenQ projector or
using ethernet instead of WiFi.

## Supported projectors

The following projectors are known to work:

* HT4550i
* MW519
* TH585
* TK800m
* W600L
* W1070
* W1100
* W1110
* W1140
* W1250
* W4000i
* X3000i

The following projectors are not tested but use the same protocol according to the documentation:

Others in the L, P, T, W and X Series

Not supported:

* RP552
* RP552H
* RP840G
* RP653
* RP703
* RP750
* RP750K
* RP652
* RP702
* RP790S
* RP705H

Please let me know if your projector is also supported by this Home Assistant integration so I can
improve the overview of supported projectors.

## Installation

### HACS

The recommended way to install this Home Assistant integration is by using [HACS][hacs].
Click the following button to open the integration directly on the HACS integration page.

[![Install BenQ projector from HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rrooggiieerr&repository=homeassistant-benqprojector&category=integration)

Or follow these instructions:

- Go to your **HACS** view in Home Assistant and then to **Integrations**
- Select **+ Explore & download repositories** and search for *BenQ Projector*
- Select **Download**
- Restart Home Assistant

### Manually

- Copy the `custom_components/benqprojector` directory of this repository into the
`config/custom_components/` directory of your Home Assistant installation
- Restart Home Assistant

## Adding a new BenQ projector

- After restarting go to **Settings** then **Devices & Services**
- Select **+ Add integration** and type in *BenQ Projector*
- Select the serial port or enter the path manually
- Enter the baud rate
- Select **Submit**

When your wiring is right a new BenQ Projector integration and device will now be added to your
Integrations view. If your wiring is not right you will get a *Failed to connect* error message.

Some projectors need to be **on** to be able to detect the model and the integration to work.

## Actions

The integration supports actions so commands can be send which are (not yet) implemented.

`benqprojector.send` This action allows you to send commands with or withouth action to your BenQ
Projector. To get the current state of a setting use `?` as the action.

```
action: benqprojector.send
data:
  device_id: 1481637509cb0c89ea1582e195fe6370
  command: "pow"
  action: "?"
```

`benqprojector.send_raw` This action allows you to send any raw command to your BenQ Projector. The
command needs to include the `*` and `#` prefix and suffix.

```
action: benqprojector.send_raw
data:
  device_id: 1481637509cb0c89ea1582e195fe6370
  command: "*pow=?#"
```

## Contribution and appreciation

### Contribute your language

If you would like to use this Home Assistant integration in your own language you can provide a
translation file as found in the `custom_components/benqprojector/translations` directory. Create a
pull request (preferred) or issue with the file for your language attached.

More on translating custom integrations can be found
[here](https://developers.home-assistant.io/docs/internationalization/custom_integration/).

### Contribute your projector model configuration

For increased support of your specific BenQ projector model you can contribute the configuration of
your projector to the underlaying [BenQ projector library](https://github.com/rrooggiieerr/benqprojector.py)

Follow [these instruction](https://github.com/rrooggiieerr/benqprojector.py#detecting-your-projector-capabilities)
on how to do so.

### Star this integration

Help other Home Assistant users find this integration by starring this GitHub page. Click **⭐ Star**
on the top right of the GitHub page.

### Support my work

Do you enjoy using this Home Assistant integration? Then consider supporting my work using one of
the following platforms, your donation is greatly appreciated and keeps me motivated:

[![Github Sponsors][github-shield]][github]
[![PayPal][paypal-shield]][paypal]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Patreon][patreon-shield]][patreon]

### Hire me

If you would like to have a Home Assistant integration developed for your product or are in need
for a freelance Python developer for your project please contact me, you can find my email address
on [my GitHub profile](https://github.com/rrooggiieerr).

[python-shield]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[releases]: https://github.com/rrooggiieerr/homeassistant-benqprojector/releases
[releases-shield]: https://img.shields.io/github/v/release/rrooggiieerr/homeassistant-benqprojector?style=for-the-badge
[license]: ./LICENSE
[license-shield]: https://img.shields.io/github/license/rrooggiieerr/homeassistant-benqprojector?style=for-the-badge
[maintainer]: https://github.com/rrooggiieerr
[maintainer-shield]: https://img.shields.io/badge/MAINTAINER-%40rrooggiieerr-41BDF5?style=for-the-badge
[homeassistant]: https://www.home-assistant.io/
[homeassistant-shield]: https://img.shields.io/badge/home%20assistant-%2341BDF5.svg?style=for-the-badge&logo=home-assistant&logoColor=white
[hacs]: https://hacs.xyz/
[hacs-shield]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[paypal]: https://paypal.me/seekingtheedge
[paypal-shield]: https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white
[buymecoffee]: https://www.buymeacoffee.com/rrooggiieerr
[buymecoffee-shield]: https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black
[github]: https://github.com/sponsors/rrooggiieerr
[github-shield]: https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA
[patreon]: https://www.patreon.com/seekingtheedge/creators
[patreon-shield]: https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white
