# Phishing Avoidance Project 🏰
An Android application and a Stress recognition API combination to practice the research about phishing avoidance with general devices.  (by processing the PPG data sent from the client-side)

## Workflow Chart
![workflow](https://user-images.githubusercontent.com/24470452/111409486-ea615680-873b-11eb-900e-efc6afdabfe3.png)

## Terminologies
Phishing: Phishing is the fraudulent attempt to obtain sensitive information or data, such as usernames, passwords and credit card details or other sensitive details, by impersonating oneself as a trustworthy entity in a digital communication. (From [Wikipedia!](https://en.wikipedia.org/wiki/Phishing#:~:text=Phishing%20is%20the%20fraudulent%20attempt,entity%20in%20a%20digital%20communication.))[1]
PPG: Photoplethysmography (PPG) is a simple optical technique used to detect volumetric changes in blood in the peripheral circulation. It is a low-cost and non-invasive method that makes measurements at the surface of the skin. The technique provides valuable information related to our cardiovascular system. (From [News Medical!](https://www.news-medical.net/health/Photoplethysmography-(PPG).aspx#:~:text=Photoplethysmography%20(PPG)%20is%20a%20simple,related%20to%20our%20cardiovascular%20system.))[2]
HRV: Heart rate variability is literally the variance in time between the beats of your heart. (From [Whoop!](https://www.whoop.com/thelocker/heart-rate-variability-hrv/#:~:text=Heart%20rate%20variability%20is%20literally,1.15%20seconds%20between%20two%20others.))[3]
OH1-polar watch: Polar OH1 is an optical heart rate monitor that combines versatility, comfort and simplicity. You can use it both as a standalone device and pair it with various fitness apps, sports watches and smart watches, thanks to Bluetooth® and ANT+ connectivity[6].


## How to detect stress level

We can use some features to detect the stress level of people, like photoplethysmogram (PPG), electrodermal activity (EDA), and skin temperature (SKT). In general, stress is an important factor that can influence the autonomic nervous system (ANS). Heart-rate variability (HRV) is known to be related to ANS activity, so we used an HRV derived from the PPG peak interval. In addition, the peak characteristics of the skin conductance (SC) from EDA and SKT variation can also reflect ANS activity[4].

Evidence shows that HRV is related to stress level, Daniel et al. found that Significantly higher normalized low-frequency HRV components and breathing rates were measured in the stress condition when compared to the rest condition[5].

For now, we only have limted devices: Some phones(Samsung Galaxy A01 with Android 10 version), Some polar watches(OHR Sensor POL OH1 Plus Blk). Therefore, based on these devices, we can get the heart rate and PPG data from these devices. see the example result(exampleData.csv)

Therefore, based on these things, we try to use PPG data from the watch to calculate the HRV data. It is not easy to process PPG data, but we found Neurokit2 kit[7] can be used to get the HRV data by processing PPG data. Then, we can use this HRV data to analyse the stress level.

## Reference
1.https://en.wikipedia.org/wiki/Phishing#:~:text=Phishing%20is%20the%20fraudulent%20attempt,entity%20in%20a%20digital%20communication.  
2.https://www.news-medical.net/health/Photoplethysmography-(PPG).aspx#:~:text=Photoplethysmography%20(PPG)%20is%20a%20simple,related%20to%20our%20cardiovascular%20system.    
3.https://www.whoop.com/thelocker/heart-rate-variability-hrv/#:~:text=Heart%20rate%20variability%20is%20literally,1.15%20seconds%20between%20two%20others.  
4.Huynh, S., Balan, R. K., Ko, J., & Lee, Y. (2019, November). VitaMon: Measuring heart rate variability using smartphone front camera. In Proceedings of the 17th Conference on Embedded Networked Sensor Systems (pp. 1-14).  
5.McDuff, D., Gontarek, S., & Picard, R. (2014, August). Remote measurement of cognitive stress via heart rate variability. In 2014 36th Annual International Conference of the IEEE Engineering in Medicine and Biology Society (pp. 2957-2960). IEEE.  
6.https://www.polar.com/en/products/accessories/oh1-optical-heart-rate-sensor
7.https://neurokit2.readthedocs.io/en/latest/functions.html#neurokit2.hrv 
