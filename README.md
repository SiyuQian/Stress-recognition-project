# Stress detection project 🏰
This project includes an Android application and a stress recognition API combination to provide a solution using mobile and wearable devices to detect the participants' stress level.

**Background**

Phishing is recognised as a serious threat to organisations and individuals. While there have been significant technical advances in blocking phishing attacks, people remain the last line of defence and there is a gap in understanding the factors that cause humans to be vulnerable. To study the underlying causes for phishing attacks, we are going to conduct phishing experiments on the campus. 

This year, during the first stage, we will run several simulated phishing attacks on all the staff in UoA, and we aimed to find the group of users that are more susceptible to phishing (which will be the ones who fall for the attacks), and investigate deeper into their behaviours and physical/cognitive state on why they fall for phishing attacks.

For the second stage, we planned to conduct a diary study that runs for 1 or 2 weeks and recruit participants from the users who fall for the attack during the first stage.  The participants would be asked to work as usual, but with devices mounted on them (POlar OH1) or on their workplace (smartphone). We will use those devices to collect their physical and biological data such as their heart rate, or PPG, or the environmental data. During the experiment, we want to collect as much information as possible.

Currently, the smartphone is been used as a middleware that collects and stores all the data. It can be connected to a Polar OH1 wristband for collecting their PPG signal (for measuring stress, and HR).

We want to investigate the feasibility to use the smartphone camera to collect more data from the user, for example, using facial emotion recognition technology to find out the users current emotional state (whether he/she is stressed or not, or depressed etc.), or using the TOI technology to capture the heart rate changes via colour changes due to blood flow, or even using an eye-tracking API or technology to record the user’s eye saccade to measure his/her stress level (or current cognitive load). 

With these data at hand, we want to study whether the user’s cognitive state (emotional state or stress level) would have an impact on users behaviour, and thus influence their detection accuracy and phishing susceptibility.


**Features**

* Generate METADATA and line chart for the recorded data automatically
* Real time calculation of HRV based on PPG data
* Multiple algorithms for detecting stress:
   * Stress Detection Algorithm
   * Sliding Window Algorithm

## Workflow Chart
![workflow](https://user-images.githubusercontent.com/24470452/121450352-afe02080-c9ef-11eb-8a16-e93629e50063.png)

## Terminologies
PPG: Photoplethysmography (PPG) is a simple optical technique used to detect volumetric changes in blood in the peripheral circulation. It is a low-cost and non-invasive method that makes measurements at the surface of the skin. The technique provides valuable information related to our cardiovascular system. (From [News Medical](https://www.news-medical.net/health/Photoplethysmography-(PPG).aspx#:~:text=Photoplethysmography%20(PPG)%20is%20a%20simple,related%20to%20our%20cardiovascular%20system.))[2]
  
HRV: Heart rate variability is literally the variance in time between the beats of your heart. (From [Whoop](https://www.whoop.com/thelocker/heart-rate-variability-hrv/#:~:text=Heart%20rate%20variability%20is%20literally,1.15%20seconds%20between%20two%20others.))[3]
  
OH1-polar watch: Polar OH1 is an optical heart rate monitor that combines versatility, comfort and simplicity. You can use it both as a standalone device and pair it with various fitness apps, sports watches and smart watches, thanks to Bluetooth® and ANT+ connectivity[6].


## How to detect stress level

We can use some features to detect the stress level of people, like photoplethysmogram (PPG), electrodermal activity (EDA), and skin temperature (SKT). In general, stress is an important factor that can influence the autonomic nervous system (ANS). Heart-rate variability (HRV) is known to be related to ANS activity, so we used an HRV derived from the PPG peak interval. In addition, the peak characteristics of the skin conductance (SC) from EDA and SKT variation can also reflect ANS activity[4].

Evidence shows that HRV is related to stress level, Daniel et al. found that Significantly higher normalized low-frequency HRV components and breathing rates were measured in the stress condition when compared to the rest condition[5].

For now, we only have limted devices: Some phones(Samsung Galaxy A01 with Android 10 version), Some polar watches(OHR Sensor POL OH1 Plus Blk). Therefore, based on these devices, we can get the heart rate and PPG data from these devices. see the example result(exampleData.csv)

Therefore, based on these things, we try to use PPG data from the watch to calculate the HRV data. It is not easy to process PPG data, but we found Neurokit2 kit[7] can be used to get the HRV data by processing PPG data. Then, we can use this HRV data to analyse the stress level.

## Run the Android App
Firstly, Open the client in the Android App, and run it on the real android app like our test phone(Samsung Galaxy A01).
After downloaded the application on the phone, make sure the permission of all things is opened, buletooth of the phone is opened.
Then, you need to wear the watch(OHR Sensor POL OH1 Plus Blk) and open it, if you do not konw how to wear the watch, please see [this](https://www.polar.com/en/products/accessories/oh1-optical-heart-rate-sensor). 
Finally, connect the watch to the app that we already downloaded, click the 'start recording' button and it will run successfully. 

## Run the server
## Getting start with Docker
This project was bootstrapped with [Docker](https://www.docker.com/get-started).
## Available Scripts
In the project directory, you can run:
### `docker-compose -f docker-compose.yml up` in the server file

## Reference
1.https://en.wikipedia.org/wiki/Phishing#:~:text=Phishing%20is%20the%20fraudulent%20attempt,entity%20in%20a%20digital%20communication.  
2.https://www.news-medical.net/health/Photoplethysmography-(PPG).aspx#:~:text=Photoplethysmography%20(PPG)%20is%20a%20simple,related%20to%20our%20cardiovascular%20system.    
3.https://www.whoop.com/thelocker/heart-rate-variability-hrv/#:~:text=Heart%20rate%20variability%20is%20literally,1.15%20seconds%20between%20two%20others.  
4.Huynh, S., Balan, R. K., Ko, J., & Lee, Y. (2019, November). VitaMon: Measuring heart rate variability using smartphone front camera. In Proceedings of the 17th Conference on Embedded Networked Sensor Systems (pp. 1-14).  
5.McDuff, D., Gontarek, S., & Picard, R. (2014, August). Remote measurement of cognitive stress via heart rate variability. In 2014 36th Annual International Conference of the IEEE Engineering in Medicine and Biology Society (pp. 2957-2960). IEEE.  
6.https://www.polar.com/en/products/accessories/oh1-optical-heart-rate-sensor
7.https://neurokit2.readthedocs.io/en/latest/functions.html#neurokit2.hrv 
