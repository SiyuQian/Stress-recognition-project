package com.szhu842.hr_ppg_monitor;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.util.Log;
import android.widget.Toast;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import com.android.volley.toolbox.JsonArrayRequest;
import com.opencsv.CSVWriter;

import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.Response;
import com.android.volley.VolleyError;
import com.android.volley.toolbox.Volley;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.reactivestreams.Publisher;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

import io.reactivex.rxjava3.android.schedulers.AndroidSchedulers;
import io.reactivex.rxjava3.disposables.Disposable;
import io.reactivex.rxjava3.functions.Function;
import polar.com.sdk.api.PolarBleApi;
import polar.com.sdk.api.PolarBleApiCallback;
import polar.com.sdk.api.PolarBleApiDefaultImpl;
import polar.com.sdk.api.errors.PolarInvalidArgument;
import polar.com.sdk.api.model.PolarAccelerometerData;
import polar.com.sdk.api.model.PolarDeviceInfo;
import polar.com.sdk.api.model.PolarHrData;
import polar.com.sdk.api.model.PolarOhrPPGData;
import polar.com.sdk.api.model.PolarOhrPPIData;
import polar.com.sdk.api.model.PolarSensorSetting;

public class DataService extends Service {
    /**
     * The server URL of the API that process the PPG data
     */
    public static final String SERVER_URL = "http://192.168.1.65/api/v1/stress?mode=hrv";

    /**
     * The frequency of sending the HTTP requests
     */
    public static final int FREQUENCY = 59;

    /**
     * The boolean flag to determine if a request is sent for the current second
     */
    public boolean isSend = false;

    /**
     * The storage to save the current second
     */
    public int secondStorage = 0;

    /**
     * The HTTP request data container
     */
    public JSONArray httpRequestData = new JSONArray();


    public PolarBleApi api;
    private String TAG = "DataService";
//    private Context classContext;
    private String uu_id;
    private Disposable ppgDisposable = null;
    private Disposable accDisposable = null;
    private Disposable ppiDisposable = null;

    private boolean sent = false;

    private float ppgData = 0.0f;
    private float ppiData = 0.0f;
    private int accX = 0;
    private int accY = 0;
    private int accZ = 0;
    private int hr = 0;

    private String battery = "";

    private String DEVICE_ID;
    private String fileName;
    private String deviceName;

    private final String CHANNEL_ID = "com.szhu842";
    private final String CHANNEL_NAME = "data channel";
    private final int NOTIFICATION_ID = 1;
    private int counter;
    private int inumber;
    private long startTime;
    public JSONObject jsdata;

    public DataService() {
    }

//    public DataService(Context context, String id) {
//        super();
//
//
//        this.classContext = context;
//        this.DEVICE_ID = id;
//        Log.d(TAG, "constructor " + DEVICE_ID);
//
//    }

    @Override
    public void onCreate() {
        super.onCreate();
        SharedPreferences shardPref = getSharedPreferences(MainActivity.MyPREFERENCES,Context.MODE_PRIVATE);
        DEVICE_ID = shardPref.getString("deviceID", "default");

        Log.d(TAG, "onCreate: " + DEVICE_ID);
        IntentFilter filter = new IntentFilter();
        filter.addAction("sendingState");
        filter.addAction("requestUpdate");
        filter.addAction("turnoffService");
        filter.addAction("onResume");
        filter.addAction("onPause");
        registerReceiver(receiver, filter);
        startForegroundService();
    }

    @Override
    public void onDestroy() {

        Intent broadcastIntent = new Intent();
        broadcastIntent.setAction("restartservice");
        broadcastIntent.setClass(this, Restarter.class);
        this.sendBroadcast(broadcastIntent);
        unregisterReceiver(receiver);

        super.onDestroy();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        super.onStartCommand(intent, flags, startId);
//
//        if (null == intent | intent.getStringExtra("id") == null) {
//            String source = null == intent ? "intent" : "action";
//            Log.e(TAG, source + " was null, flags=" + flags + " bits=" + Integer.toBinaryString(flags));
//            return START_STICKY;
//        }
//        DEVICE_ID = intent.getStringExtra("id");
        setupPolar();

        return START_STICKY;
    }

    private void startForegroundService() {

        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0,
                new Intent(this, DataCollector.class), PendingIntent.FLAG_UPDATE_CURRENT);

        //create the Notification

        NotificationChannel notificationChannel;
        Notification notification;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            notificationChannel = new NotificationChannel(CHANNEL_ID,
                    CHANNEL_NAME, NotificationManager.IMPORTANCE_HIGH);
            notificationChannel.setShowBadge(true);
            notificationChannel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            manager.createNotificationChannel(notificationChannel);

            notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                    .setContentTitle("sensorDataCollector")
                    .setContentText("The service is running in background")
                    .setSmallIcon(R.drawable.icon2)
                    .setContentIntent(pendingIntent)
                    .build();
        } else {
            notification = new Notification.Builder(this)
                    .setContentTitle("sensorDataCollector")
                    .setContentText("The service is running in background")
                    .setSmallIcon(R.drawable.icon2)
                    .setContentIntent(pendingIntent)
                    .build();
        }

        //display the notification
        if (Build.VERSION.SDK_INT >= 26) {
            startForegroundService(new Intent(DataService.this, DataService.class));
        }
        startForeground(NOTIFICATION_ID, notification);
        ;

    }

    public void setupPolar() {
        Log.d(TAG, "setupPolar: entered");

        if (api == null) {
            Log.d(TAG, "setupPolar: ");
            api = PolarBleApiDefaultImpl.defaultImplementation(this,
                    PolarBleApi.ALL_FEATURES);

            api.setAutomaticReconnection(true);

            api.setApiCallback(new PolarBleApiCallback() {
                @Override
                public void blePowerStateChanged(boolean b) {
                    Log.d(TAG, "BluetoothStateChanged " + b);
                }

                @Override
                public void deviceConnected(PolarDeviceInfo s) {
                    Log.d(TAG, "Device connected " + s.deviceId);
                    Toast.makeText(getApplicationContext(), "connected",
                            Toast.LENGTH_SHORT).show();
                    deviceName = s.deviceId;
                    setDeviceName(s.deviceId);
                    Intent intent = new Intent("updatingState");
                    intent.putExtra("name", deviceName);
                    sendBroadcast(intent);
                }

                @Override
                public void deviceConnecting(PolarDeviceInfo polarDeviceInfo) {

                }

                @Override
                public void deviceDisconnected(PolarDeviceInfo s) {
                    Log.d(TAG, "Device disconnected" + s);

                    Intent intent = new Intent("updatingState");
                    intent.putExtra("name", "Disconnected");
                    sendBroadcast(intent);

                    if (sent) {
                        try {
                            api.connectToDevice(DEVICE_ID);
                        } catch (PolarInvalidArgument polarInvalidArgument) {
                            polarInvalidArgument.printStackTrace();
                        }
                    }


                }

                @Override
                public void ecgFeatureReady(String s) {
                    Log.d(TAG, "ECG Feature ready" + s);

                }

                @Override
                public void accelerometerFeatureReady(String s) {
                    Log.d(TAG, "ACC Feature ready " + s);
                    streamACC();
                }

                @Override
                public void ppgFeatureReady(String s) {
                    Log.d(TAG, "PPG Feature ready " + s);
                    streamPPG();
                }

                @Override
                public void ppiFeatureReady(String s) {
                    Log.d(TAG, "PPI Feature ready " + s);
//                    streamPPI();
                }

                @Override
                public void biozFeatureReady(String s) {
                    Log.d(TAG, "bioz Feature ready " + s);
                }

                @Override
                public void hrFeatureReady(String s) {
                    Log.d(TAG, "HR Feature ready " + s);
                }

                @Override
                public void disInformationReceived(String s, UUID u, String s1) {
                    if (u.equals(UUID.fromString("00002a28-0000-1000-8000-00805f9b34fb"))) {
                        String msg = "Firmware: " + s1.trim();
                        Log.d(TAG, "Firmware: " + s + " " + s1.trim());
//                    textViewFW.append(msg + "\n");
                    }
                }

                @Override
                public void batteryLevelReceived(String s, int i) {
                    String msg = "ID: " + s + "\nBattery level: " + i;
                    Log.d(TAG, "Battery level " + s + " " + i);
                    battery = i + "";

                    Intent intent = new Intent("updatingState");
                    intent.putExtra("battery", battery);
                    sendBroadcast(intent);

                }

                @Override
                public void hrNotificationReceived(String s,PolarHrData polarHrData) {
                    hr = polarHrData.hr;
                    Log.d(TAG, "HR " + polarHrData.hr);

                    Intent intent = new Intent("updatingState");
                    intent.putExtra("hr", String.valueOf(hr));
                    sendBroadcast(intent);

                }

                @Override
                public void polarFtpFeatureReady(String s) {
                    Log.d(TAG, "Polar FTP ready " + s);
                }
            });
        }

        try {
            System.out.println(this.DEVICE_ID);
            api.connectToDevice(DEVICE_ID);
        } catch (PolarInvalidArgument a) {
            a.printStackTrace();
        }


    }

    public void streamPPG() {
        if (ppgDisposable == null) {
            Log.d(TAG, "streamPPG: start");
            ppgDisposable =
                    api.requestPpgSettings(DEVICE_ID).toFlowable().flatMap((Function<PolarSensorSetting,
                            Publisher<PolarOhrPPGData>>) sensorSetting -> api.startOhrPPGStreaming(DEVICE_ID,
                            sensorSetting.maxSettings())).observeOn(AndroidSchedulers.mainThread()).subscribe(
                            polarPPGData -> {
                                for (PolarOhrPPGData.PolarOhrPPGSample data : polarPPGData.samples) {
//                                        ppgDataObservable.onNext(data);
                                    ppgData = (data.ppg0 + data.ppg1 + data.ppg2) / 3.0f;

                                    Intent intent = new Intent("updatingState");
                                    intent.putExtra("ppg", String.valueOf(ppgData));
                                    sendBroadcast(intent);
                                     if (sent) {
                                       //writeToCsv();
                                       postRequest();

                                     }
                                }
                            },
                            throwable -> {
                                Log.e(TAG,
                                        "ppg error: " + throwable.getLocalizedMessage());
                                ppgDisposable = null;
                            },
                            () -> Log.d(TAG, "complete")
                    );
        } else {
            // NOTE stops streaming if it is "running"
            Log.d(TAG, "streamPPG: not null");
            ppgDisposable.dispose();
            ppgDisposable = null;
        }
    }

    /**
     * 20s per HTTP request
     * The request should contain all the data generated between the current and last request
     * request body example:
     * [
     *  {
     *    "Device": "712AF22B",
     *     "TimeDate": "Apr 16,2021 18:31:17:756",
     *     "Time": "0:0:4:4",
     *     "PPG": 293451,
     *     "HR": 92,
     *     "AccX": -855,
     *     "AccY": 418,
     *     "AccZ": 247,
     *     "uuid": "88dae6c7-da57-4616-8edc-369b814e37cb"
     *  },
     *  {
     *     "Device": "712AF22B",
     *     "TimeDate": "Apr 16,2021 18:31:17:756",
     *     "Time": "0:0:4:4",
     *     "PPG": 293451,
     *     "HR": 92,
     *     "AccX": -855,
     *     "AccY": 418,
     *     "AccZ": 247,
     *     "uuid": "88dae6c7-da57-4616-8edc-369b814e37cb"
     *  },
     *  ...
     * ]
     */
    public void postRequest() {
        long timeMillis = System.currentTimeMillis();
        SimpleDateFormat sdf = new SimpleDateFormat("MMM dd,yyyy HH:mm:ss:SSS", Locale.ENGLISH);
        Date resultdate = new Date(timeMillis);
        String timeDate = sdf.format(resultdate) + "";
        long resulttime = timeMillis - startTime;
        int seconds = (int) (resulttime / 1000) % 60 ;
        int minutes = (int) ((resulttime / (1000*60)) % 60);
        int hours   = (int) ((resulttime / (1000*60*60)) % 24);
        String time = hours + ":" + minutes + ":" + seconds + ":" + (resulttime%1000);

        Log.d(deviceName,"deviceName");
        Log.d(timeDate,"timeDate");
        Log.d(time,"time");
        Log.d(String.valueOf(ppgData),"ppgData");


        /**
         * when the counter having the remainder of 20 then the program should send the request
         * e.g 0s, 20s, 40s, 60s
         */
        Log.d(String.valueOf(timeMillis % FREQUENCY), "remainder");

        /**
         * Update the second storage every second
         * If the second is past, then reset the isSend flag
         */
        if (seconds != secondStorage) {
            secondStorage = seconds;
            isSend = false;
        }

        if (seconds % FREQUENCY == 0 && seconds != 0 && !isSend) {
            Log.d(String.valueOf(counter),"CounterIn20");

            /**
             * Execute the Async task to send out the HTTP request
             */
            RequestQueue requestQueue = Volley.newRequestQueue(DataService.this);
            JsonArrayRequest jsonArrayRequest = new JsonArrayRequest(Request.Method.POST, SERVER_URL, httpRequestData, new Response.Listener<JSONArray>() {
                @Override
                public void onResponse(JSONArray response) {
                    System.out.println("success" + response);
                }
            }, new Response.ErrorListener() {
                @Override
                public void onErrorResponse(VolleyError error) {
                    Log.d("RESP", "onResponse: " + error);
                }
            });
            requestQueue.add(jsonArrayRequest);
            requestQueue.cancelAll(jsonArrayRequest);

            /**
             * Update isSend value if the request is already sent for the current second
             */
            isSend = true;

            /**
             * Reset HTTP request data
             */
            httpRequestData = new JSONArray();
//            new ReuqestSender().execute(httpRequestData);
        } else {
            Log.d(String.valueOf(counter),"CounterInEvery");
            /**
             * Create the JSON array which will be sent to the server end
             */
            try {
                // The single JSON object contains the data
                JSONObject postData = new JSONObject();
                postData.put("Device", deviceName);
                postData.put("TimeDate",timeDate);
                postData.put("Time",time);
                postData.put("PPG", String.valueOf(ppgData));
                postData.put("HR",String.valueOf(hr));
                postData.put("uuid",uu_id);

                httpRequestData.put(postData);
//                Log.d(String.valueOf(postData), "postData");
//                Log.d(String.valueOf(httpRequestData), "httpRequestData");
            } catch (JSONException e) {
                e.printStackTrace();
            }
        }

        counter++;
        Log.d(String.valueOf(counter),"counter");
    }

    public void streamACC() {
        if (accDisposable == null) {
            accDisposable =
                    api.requestAccSettings(DEVICE_ID).toFlowable().flatMap((Function<PolarSensorSetting,
                            Publisher<PolarAccelerometerData>>) sensorSetting -> api.startAccStreaming(DEVICE_ID,
                            sensorSetting.maxSettings())).observeOn(AndroidSchedulers.mainThread()).subscribe(
                            polarACCData -> {
                                for (PolarAccelerometerData.PolarAccelerometerSample data : polarACCData.samples) {
//                                        accData = data;
//                                        accDataObservable.onNext(data);
                                    accX = data.x;
                                    accY = data.y;
                                    accZ = data.z;
                                }
                            },
                            throwable -> {
                                Log.e(TAG,
                                        "" + throwable.getLocalizedMessage());
                                accDisposable = null;
                            },
                            () -> Log.d(TAG, "complete")
                    );
        } else {
            // NOTE stops streaming if it is "running"
            accDisposable.dispose();
            accDisposable = null;
        }
    }

    public void streamPPI() {
        if (ppiDisposable == null) {

            ppiDisposable = api.startOhrPPIStreaming(DEVICE_ID).observeOn(AndroidSchedulers.mainThread()).subscribe(
                    polarPPIData -> {
                        for (PolarOhrPPIData.PolarOhrPPISample data : polarPPIData.samples) {
//                                ppiDataObservable.onNext(data);
                            ppiData = data.ppi;
                        }
                    },
                    throwable -> {
                        Log.e(TAG,
                                "" + throwable.getLocalizedMessage());
                        ppiDisposable = null;
                    },
                    () -> Log.d(TAG, "complete")
            );


        } else {
            // NOTE stops streaming if it is "running"
            ppiDisposable.dispose();
            ppiDisposable = null;
        }
    }


    public void setDeviceName(String s) {
        deviceName = s;
        startTime = System.currentTimeMillis();
        SimpleDateFormat sdf = new SimpleDateFormat("MMM,dd_HH-mm-ss", Locale.ENGLISH);
        Date resultdate = new Date(startTime);
        fileName = s + "_" + sdf.format(resultdate);
        Log.d(TAG, "setDeviceName: " + fileName + ".csv");
    }

    public void writeToCsv() {
        if (sent) {
            String csvRoot = (Environment.getExternalStorageDirectory().getAbsolutePath() + "/PPGData"); // Here csv file name is MyCsvFile.csv
            File csvFolder = new File(csvRoot);
            if (!csvFolder.exists()) {
                csvFolder.mkdir();
                Log.d(TAG, "writeToCsv: making dir");
            }
            String filePath = csvRoot + "/" + fileName + ".csv";
            Log.d(TAG, "writeToCsv: " + filePath);
            File csvFile = new File(filePath);
            if (!csvFile.exists()) {

                CSVWriter writer = null;
                try {
                    writer = new CSVWriter(new FileWriter(csvFile));
                    List<String[]> data = new ArrayList<String[]>();
                    data.add(new String[]{"Device", "TimeDate", "Time", "PPG", "HR", "AccX", "AccY", "AccZ"});
                    writer.writeAll(data); // data is adding to csv

                    writer.close();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
            CSVWriter writer = null;
            try {
                writer = new CSVWriter(new FileWriter(csvFile, true));
                long timeMillis = System.currentTimeMillis();
                SimpleDateFormat sdf = new SimpleDateFormat("MMM dd,yyyy HH:mm:ss:SSS", Locale.ENGLISH);
                Date resultdate = new Date(timeMillis);
                String timeDate = sdf.format(resultdate) + "";
                long resulttime = timeMillis - startTime;
                int seconds = (int) (resulttime / 1000) % 60 ;
                int minutes = (int) ((resulttime / (1000*60)) % 60);
                int hours   = (int) ((resulttime / (1000*60*60)) % 24);
                String time = hours + ":" + minutes + ":" + seconds + ":" + (resulttime%1000);

                List<String[]> data = new ArrayList<String[]>();
                data.add(new String[]{deviceName, timeDate, time, String.valueOf(ppgData),
                        String.valueOf(hr), String.valueOf(accX), String.valueOf(accY),
                        String.valueOf(accZ)});

                writer.writeAll(data); // data is adding to csv

                writer.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }

    }

    public void startSending() {
        sent = true;
//        streamPPG();
        startTime = System.currentTimeMillis();

        Log.d(TAG, "startSending: " + sent);
//        if (ppgDisposable.isDisposed()){
//            streamPPG();
//        }
//
//        if (ppgDisposable == null){
//            Log.d(TAG, "startSending: null");
//            streamPPG();
//        } else {
//            Log.d(TAG, "startSending: " + ppgDisposable.isDisposed());
//        }
    }

    public void stopSending() {
        sent = false;
        stopForeground(true);
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }


    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            if (action.equals("sendingState")) {
                uu_id= intent.getStringExtra("gotUuid");
                intent.putExtra("uu_id",uu_id);
                Log.d("uuid",uu_id);
                if (intent.getBooleanExtra("sent", false)) {
                    startSending();
                } else {
                    stopSending();
                }

            } else if (action.equals("requestUpdate")) {
                Intent sendintent = new Intent("updatingState");
                sendintent.putExtra("name", deviceName);
                sendintent.putExtra("battery", battery);
                sendintent.putExtra("ppg", String.valueOf(ppgData));
                sendintent.putExtra("hr", String.valueOf(hr));
                sendintent.putExtra("buttonState", String.valueOf(sent));
                sendBroadcast(sendintent);
            } else if (action.equals("turnoffService")) {
                Log.d(TAG, "onReceive: turnoffService");
                stopSending();
                Intent sendintent = new Intent("updatingState");
                sendintent.putExtra("buttonState", String.valueOf(sent));
                sendBroadcast(sendintent);
//                ppgDisposable.dispose();
//                Log.d(TAG, "onReceive: " + ppgDisposable.isDisposed());

//                try {
//                    api.disconnectFromDevice(DEVICE_ID);
//                } catch (PolarInvalidArgument polarInvalidArgument) {
//                    polarInvalidArgument.printStackTrace();
//                }
                api.shutDown();
                stopSelf();
            } else if (action.equals("onPause")) {
                if (api != null) {
                    api.backgroundEntered();
                }
            }else if (action.equals("onResume")) {
                if (api != null) {
                    api.foregroundEntered();
                }
            }
        }
    };


//
//
//
//    api.requestAccSettings(s).observeOn(AndroidSchedulers.mainThread()).toFlowable().flatMap((Function<PolarSensorSetting, Flowable<Map<PolarSensorSetting.SettingType, Integer>>>) sensorSetting -> {
//        Log.d(TAG,"acc max available: " + sensorSetting.maxSettings().settings);
//        return Flowable.just(maxSettingsSingle(sensorSetting));
//    }).observeOn(AndroidSchedulers.mainThread()).flatMap((Function<Map<PolarSensorSetting.SettingType, Integer>, Publisher>) selected -> {
//        String name = Objects.requireNonNull(sensStringTextViewMap.get(s)).name;
//        Objects.requireNonNull(dataCollectorMap.get(s)).startAccStream(name);
//        return api.startAccStreaming(s,new PolarSensorSetting(selected));
//    }).buffer(2,1).observeOn(AndroidSchedulers.mainThread()).map(new Function<List, List<Pair<Long, PolarAccelerometerData.PolarAccelerometerSample>>>() {
//        @override
//        public List<Pair<Long, PolarAccelerometerData.PolarAccelerometerSample>> apply(List datas) throws Throwable {
//            long delta1 = ((datas.get(1).timeStamp - datas.get(0).timeStamp) / datas.get(1).samples.size());
//            long baseTimeStamp1 = datas.get(0).timeStamp - ((datas.get(0).samples.size()-1)*delta1);
//            List<Pair<Long, PolarAccelerometerData.PolarAccelerometerSample>> list = new ArrayList<>();
//            for(PolarAccelerometerData.PolarAccelerometerSample sample : datas.get(0).samples){
//                list.add(new Pair<>(baseTimeStamp1,sample));
//                baseTimeStamp1 += delta1;
//            }
//            return list;
//        }}).observeOn(AndroidSchedulers.mainThread()).subscribe(
//            pairs -> {
//    },
//    throwable -> {},
//            () -> {
//
//    }
//    );



}
