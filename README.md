# Stress detection project 🏰
This project aimed to us collected PPG signals to calculate the user's stress level. This project includes an Android application and a stress recognition API. The Android App is used to collect sensory data from a specific health tracker (Polar OH 1). Currently, the smartphone is been used as a middleware that collects and stores all the data. The API is responsible for storing the data collected and performing calculations to convert PPG signals to HRV related features (mainly RMSSD and pNN50) for calculating stress levels.

**Background**

Phishing is recognised as a serious threat to organisations and individuals. While there have been significant technical advances in blocking phishing attacks, people remain the last line of defence, and there is a gap in understanding the factors that cause humans to be vulnerable. Studies have shown that higher stress level can lead to lower task performance. Hence, it would be reasonable to expect a decrease in the users' phishing detection performance when they are under high stress. Therefore, we aimed to use this project to collect stress level data to assess how users change their stress before and during email checking session. With this data, we can then link stress level to phishing detection performance to partially justify the users phishing susceptibility.

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

There are many ways of detecting users' stress level, such as photoplethysmogram (PPG), electrodermal activity (EDA), and skin temperature (SKT). In general, stress is an important variable that can influence the autonomic nervous system (ANS). Heart-rate variability (HRV) is known to be related to ANS activity, so we used an HRV derived from the PPG peak interval. In addition, the peak characteristics of the skin conductance (SC) from EDA and SKT variation can also reflect ANS activity[4].

Evidence shows that HRV is related to stress level, Daniel et al. found that Significantly higher normalized low-frequency HRV components and breathing rates were measured in the stress condition when compared to the rest condition[5].

We are using the following devices for testing our applications: 
- Phone: Samsung Galaxy A01 (Android 10)
- Health tracker:Polar OH 1 (wristband)
Based on these devices, we can get the heart rate and PPG data from these devices. see the example result(exampleData.csv)

Therefore, based on these things, we try to use PPG data from the watch to calculate the HRV data. It is not easy to process PPG data, but we found Neurokit2 kit[7] can be used to get the HRV data by processing PPG data. Then, we can use this HRV data to analyse the stress level.

## Run the Android App
Firstly, Open the client in the Android App, and run it on the real android app like our test phone(Samsung Galaxy A01).
After downloaded the application on the phone, make sure the permission of all things is opened, buletooth of the phone is opened.
Then, you need to wear the wristband (Polar OH 1) and open it, and make sure the phone is paired with the device. If you do not konw how to wear the watch, please see [this](https://www.polar.com/en/products/accessories/oh1-optical-heart-rate-sensor). 
Finally, connect the watch to the app that we already downloaded, click the 'start recording' button and it will run successfully. 

## How to run

## Get Started
```
# Step 1
git clone git@github.com:SiyuQian/Stress-recognition-project.git
# Step 2
cd Stress-recognition-project
# Step 3
docker-compose -f server/docker-compose.yml up
```

If you do not have the Docker installed on your computer:

[Docker](https://www.docker.com/get-started)

## Reference
1.https://en.wikipedia.org/wiki/Phishing#:~:text=Phishing%20is%20the%20fraudulent%20attempt,entity%20in%20a%20digital%20communication.  
2.https://www.news-medical.net/health/Photoplethysmography-(PPG).aspx#:~:text=Photoplethysmography%20(PPG)%20is%20a%20simple,related%20to%20our%20cardiovascular%20system.    
3.https://www.whoop.com/thelocker/heart-rate-variability-hrv/#:~:text=Heart%20rate%20variability%20is%20literally,1.15%20seconds%20between%20two%20others.  
4.Huynh, S., Balan, R. K., Ko, J., & Lee, Y. (2019, November). VitaMon: Measuring heart rate variability using smartphone front camera. In Proceedings of the 17th Conference on Embedded Networked Sensor Systems (pp. 1-14).  
5.McDuff, D., Gontarek, S., & Picard, R. (2014, August). Remote measurement of cognitive stress via heart rate variability. In 2014 36th Annual International Conference of the IEEE Engineering in Medicine and Biology Society (pp. 2957-2960). IEEE.  
6.https://www.polar.com/en/products/accessories/oh1-optical-heart-rate-sensor
7.https://neurokit2.readthedocs.io/en/latest/functions.html#neurokit2.hrv 
