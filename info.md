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

Home Assistant integration that supports sending commands to BenQ projectors over the serial
interface or serial to network bridges like [esp-link](https://github.com/jeelabs/esp-link).

<img src="https://raw.githubusercontent.com/rrooggiieerr/homeassistant-benqprojector/main/Screenshot%201b.png" style="width: 50%"/>

BenQ projectors and flat panels with a serial port can support one of three protocols. This plugin
supports projectors which are of the L, P, T, W and X series but probably also others.

## Hardware

## Features

## Protocol

This integration works if your projector supports the following command structure:

```
<CR>*<key>=<value>#<CR>
```

Where `<CR>` is a Carriage Return

Examples:  
Power on   : `<CR>*pow=on#<CR>`  
Power off  : `<CR>*pow=off#<CR>`  
Change source to HDMI: `<CR>*sour=hdmi#<CR>`  

### Serial port

You can lookup and change the baud rate in the menu of your BenQ projector.

### Network connected projectors

The commands as described above should also work over a network connection, however I don't own
such projector and have implemented the network functionality using a serial to network bridge. The
network support for native networked BenQ projectors is thus experimental. Let me know if your
network connected BenQ projector works.

Example of a serial to network bridge using a serial to TTL converter and a Wemos C3 Mini:  

<img src="https://raw.githubusercontent.com/rrooggiieerr/homeassistant-benqprojector/main/serial%20to%20network%20bridge.png">

It has to be said that a direct serial connection to the projector is much more responsive than
using a network connection, at least when using a serial to network bridge. Maybe this is different
on a native networked BenQ projector or using ethernet instead of WiFi.

### PJLink

This integration does **not** implement the PJLink protocol, but a proparitary BenQ protocol
instead. The PJLink protocol is covered by it's own integration:

[Home Assistant PJLink integration](https://www.home-assistant.io/integrations/pjlink/)

## Supported projectors

The following projectors are known to work:

* MW519
* TH585
* W1070
* W1100
* W1110
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

Some projectors need to be on to be able to detect the model and the integration to work.

Please let me know if your projector is also supported by this Home Assistant integration so I can
improve the overview of supported projectors.

## Adding a new BenQ projector

- After restarting go to **Settings** then **Devices & Services**
- Select **+ Add integration** and type in *BenQ Projector*
- Select the serial port or enter the path manually
- Enter the baud rate
- Select **Submit**

When your wiring is right a new BenQ Projector integration and device will now be added to your
Integrations view. If your wiring is not right you will get a *Failed to connect* error message.

## Contributing

If you would like to use this Home Assistant integration in your own language you can provide me
with a translation file as found in the `custom_components/benqprojector/translations` directory.
Create a pull request (preferred) or issue with the file attached.

More on translating custom integrations can be found
[here](https://developers.home-assistant.io/docs/internationalization/custom_integration/).

## Support my work

Do you enjoy using this Home Assistant integration? Then consider supporting my work using one of
the following platforms, your donation is greatly appreciated and keeps me motivated:

[![Github Sponsors][github-shield]][github]
[![PayPal][paypal-shield]][paypal]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Patreon][patreon-shield]][patreon]

## Hire me

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
