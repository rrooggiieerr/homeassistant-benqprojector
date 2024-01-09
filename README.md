# Home Assistant BenQ projector integration

Home Assistant integration that supports sending commands to BenQ projectors
over the serial interface or serial to network bridges like esp-link.

<img src="https://raw.githubusercontent.com/rrooggiieerr/homeassistant-benqprojector/main/Screenshot%201b.png" style="width: 50%"/>

BenQ projectors and flat pannels with a serial port can support one of three
protocols. This plugin supports projectors which are of the L, P, T, W and X
series but probably also others.

## Protocol

This integration works if your projector supports the following command
structure:

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

The commands as described above should also work over a network connection,
however I don't own such projector and have implemented the network
functionality using a serial to network bridge. The network support for native
networked BenQ projectors is thus experimental. Let me know if your network
connected BenQ projector works.

Example of a serial to network bridge using a serial to TTL converter and a
Wemos C3 Mini:  
<img src="https://raw.githubusercontent.com/rrooggiieerr/homeassistant-benqprojector/main/serial%20to%20network%20bridge.png">

It has to be said that a direct serial conection to the projector is much more
responsive than using a network connection, at least when using a serial to
network bridge. Maybe this is different on a native networked BenQ projector or
using ethernet instead of WiFi.

### PJLink

This integration does **not** implement the PJLink protocol, but a proparitary
BenQ protocol instead. The PJLink protocol is covered by it's own integration:
[Home Assistant PJLink integration](https://www.home-assistant.io/integrations/pjlink/)

## Supported projectors

Known to work:
* MW519
* TH585
* W1100
* W1110
* X3000i

Not tested but use te same protocol according to the documentation:  
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

Some projectors need to be on to be able to detect the model and the
integration to work.

Please let me know if your projectors is also supported by this plugin so I can
improve the overview of supported devices.

## Installation

### HACS

- Go to your **HACS** view in Home Assistant and then to **Integrations**
- Select **+ Explore & download repositories** and search for *BenQ Projector*
- Select **Download**
- Restart Home Assistant

[![Install BenQ projector from HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rrooggiieerr&repository=homeassistant-benqprojector&category=integration)

### Manually

- Copy the `custom_components/benqprojector` directory of this repository into
the `config/custom_components/` directory of your Home Assistant installation
- Restart Home Assistant

##  Adding a new BenQ projector

- After restarting go to **Settings** then **Devices & Services**
- Select **+ Add integration** and type in *BenQ Projector*
- Select the serial port or enter the path manually
- Enter the baud rate
- Select **Submit**

When your wiring is right a new BenQ Projector integration and device will now
be added to your Integrations view. If your wiring is not right you will get a
*Failed to connect* error message.

## Support my work

Do you enjoy using this Home Assistant integration? Then consider supporting
my work:  
[<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;">](https://www.buymeacoffee.com/rrooggiieerr)  
