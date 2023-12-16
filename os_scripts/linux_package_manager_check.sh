#!/bin/bash
declare -A osInfo;
osInfo[/etc/redhat-release]=dnf
osInfo[/etc/arch-release]=pacman
osInfo[/etc/gentoo-release]=emerge
osInfo[/etc/SuSE-release]=zypp
osInfo[/etc/debian_version]=apt-get
osInfo[/etc/alpine-release]=apk

# shellcheck disable=SC2068
for f in ${!osInfo[@]}
do
    if [[ -f $f ]];then
        echo ${osInfo[$f]}
    fi
done

