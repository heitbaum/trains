# HMI to GPIO

## Onboard the Radxa Cubie A5E as the interface for the HMI

### download image and burn to an sdcard
- https://github.com/armbian/community/releases/download/25.11.0-trunk.173/Armbian_community_25.11.0-trunk.173_Radxa-cubie-a5e_bookworm_edge_6.16.0_minimal.img.xz

## boot image and configure basics
```
dpkg-reconfigure tzdata
apt install lldpd vim pciutils net-tools lshw network-manager screen git
echo "DAEMON_ARGS=\"-c\"" >> /etc/default/lldpd

armbian-upgrade
reboot

wget https://github.com/radxa-pkg/aic8800/releases/download/4.0%2Bgit20250410.b99ca8b6-2/aic8800-sdio-dkms_4.0+git20250410.b99ca8b6-2_all.deb
wget https://github.com/radxa-pkg/aic8800/releases/download/4.0%2Bgit20250410.b99ca8b6-2/aic8800-firmware_4.0+git20250410.b99ca8b6-2_all.deb
dpkg -i aic8800-firmware_4.0+git20250410.b99ca8b6-2_all.deb 
dpkg -i aic8800-sdio-dkms_4.0+git20250410.b99ca8b6-2_all.deb
reboot

dpkg-reconfigure aic8800-sdio-dkms

nmcli device wifi list
nmcli device wifi connect "$SSID" password "$PASSWORD"
```

# configure mqtt

```
apt install mosquitto tcpdump

echo "listener 1883" >> /etc/mosquitto/mosquitto.conf
echo "allow_anonymous true" >> /etc/mosquitto/mosquitto.conf

apt install mosquitto-clients
mosquitto_sub -v -h broker_ip -p 1883 -t '#'

wget https://github.com/emqx/MQTTX/releases/download/v1.12.1/mqttx-cli-linux-arm64
chmod a+x mqttx-cli-linux-arm64
./mqttx-cli-linux-arm64 sub -t "/trains/track/turnout/#" -h broker_ip -p 1883

apt install python3-paho-mqtt
```
reading on the correct jmri topics

https://groups.io/g/jmriusers/topic/mqtt_connection_in_jmri/24537680?page=3&dir=desc
/trains/track/turnout/100
/trains/track/turnout/abc123
