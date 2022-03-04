#!/bin/bash

sudo nvpmodel -m 0
sudo jetson_clocks
sudo init 3
sudo sh -c 'echo 100>/sys/devices/pwm-fan/target_pwm'