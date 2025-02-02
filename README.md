# Gaffer addon

This is a minimal Gaffer add-on for Ayon pipeline integration. It uses a multi-shot switch approach, allowing you to switch the Ayon context on the fly within Gaffer - unlike other DCC integration workflows. This is especially useful when working on multiple shots or assets within the same Gaffer script as a template.

![ayon-gaffer-menu-gif](https://github.com/sosoyan/ayon-gaffer/blob/develop/ayon-gaffer-context-menu.gif)

Fundamentaly this add-on was written from scratch, however it's worth to mention that ceate, load, publish plugin modules are mostly dumped from https://github.com/RVXStudio/ayon-gaffer repository and need some refactoring before adding a new features.

## Features

- [x] Standard Ayon top menu
- [x] Context switching from top menu
- [x] Apply Script Settings and Variables and Tags from Ayon on task switch
- [x] Create, Load, Publish Gaffer Scene and Reference boxes to Ayon
- [ ] Publishing renders to Ayon

## Acknowledgments
* https://github.com/ynput
* https://github.com/RVXStudio/ayon-gaffer