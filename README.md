# Home Assistant BenQ projector integration

Home Assistant integration that supports sending commands to BenQ projectors
over the serial interface.

BenQ projectors and flat pannels with a serial port can support one of three
protocols. This plugin supports projectors which are of the L, P, T, W and X
series but probably also others.

# Protocol

This integration works if your projector has a serial port **and** supports
the following command structure: 

```
<CR>*<key>=<value>#<CR>
```

Where `<CR>` is a Cariage Return

Example:  
Power on   : `<CR>*pow=on#<CR>`  

The same commands should work over a network connection, but I don't own such
projector and have not implemented any network functionality. Contact me if
you have a network connected BenQ projector and like this to work.

### PJLink

This integration does **not** implement the PJLink protocol, but a proparitary
BenQ protocol instead. The PJLink protocol is covered by it's own integration:
[Home Assistant PJLink integration](https://www.home-assistant.io/integrations/pjlink/)

## Supported projectors

Known to work:
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

Please let me know if your projectors is also supported by this plugin so I
can improve the overview of supported devices.

## Installation

### HACS
- Go to your **HACS** view in Home Assistant and then to **Integrations**
- Open the **Custom repositories** menu
- Add this repository URL to the **Custom repositories** and select
**Integration** as the **Category**
- Click **Add**
- Restart Home Assistant

### Manually
- Copy the `custom_components/benqprojector` directory of this repository into
the `config/custom_components/` directory of your Home Assistant installation
- Restart Home Assistant

##  Adding a new BenQ projector
- After restarting go to **Settings** then **Devices & Services**
- Select **+ Add Integration** and type in *BenQ Projector*
- Select the serial port or enter the path manually
- Enter the baud rate
- Select **Submit**

When your wiring is right a new BenQ Projector integration and device will now
be added to your Integrations view. If your wiring is not right you will get a
*Failed to connect* error message.

Do you enjoy using this Home Assistant integration? Then consider supporting
my work:
[<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" >](https://www.buymeacoffee.com/rrooggiieerr)  
