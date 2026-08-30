<div align="center">
    <img src="img/drone.jpeg" alt="Photo of the Quadcopter" height="300">
    <br>
    <h3>ardupilot-rpi</h3>
    <p>
    MAVLINK Scripts used in my Ardupilot to Raspberry Pi connection for automatic video recording via Arducam.
    </p>
    <br>
    <a href="https://loganfick.com/projects/drone">See my post on my Website</a>
</div>


<!-- TABLE OF CONTENTS -->
<details open>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#description">Project Description</a></li>
    <li><a href="#files">File Structure</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>


<!-- DESCRIPTION -->
## Description

This project is a collection of scripts that uses ```pymavlink``` and ```picamera2``` to read MAVLINK status messages and record video using an Arducam camera and save to an auto-mounted USB drive.


<!-- CONTACT -->
## Files

There are 3 files in this project:

- ```companion.lua``` is the script that lives on the Ardupilot FC and runs on the drone
- ```ardupilot.py``` is the script running on the Raspberry Pi 5 Companion computer
- ```ardupilot.service``` is the linux service that automatically runs ```ardupilot.py```


<!-- CONTACT -->
## Contact

Logan Fick -  loganfickcontact@gmail.com

Project Link: [https://github.com/WeasalCrafter/ardupilot-rpi](https://github.com/WeasalCrafter/ardupilot-rpi)

Website: [https://loganfick.com/](https://loganfick.com/)


<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

This project was made with the help of Claude Code

* [Claude Code](https://claude.com/product/claude-code)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
