

Onboard the Radxa Cubie A5E as the interface for the HMI

download image from
- https://github.com/armbian/community/releases/download/25.11.0-trunk.173/Armbian_community_25.11.0-trunk.173_Radxa-cubie-a5e_bookworm_edge_6.16.0_minimal.img.xz

boot image
```
dpkg-reconfigure tzdata
apt install lldpd vim pciutils net-tools lshw network-manager screen git
echo "DAEMON_ARGS=\"-c\"" >> /etc/default/lldpd

armbian-upgrade 

wget https://github.com/radxa-pkg/aic8800/releases/download/4.0%2Bgit20250410.b99ca8b6-2/aic8800-sdio-dkms_4.0+git20250410.b99ca8b6-2_all.deb
wget https://github.com/radxa-pkg/aic8800/releases/download/4.0%2Bgit20250410.b99ca8b6-2/aic8800-firmware_4.0+git20250410.b99ca8b6-2_all.deb
dpkg -i aic8800-firmware_4.0+git20250410.b99ca8b6-2_all.deb 
dpkg -i aic8800-sdio-dkms_4.0+git20250410.b99ca8b6-2_all.deb

nmcli device wifi list
nmcli device wifi connect "$SSID" password "$PASSWORD"
```
