//package com.szhu842.hr_ppg_monitor;
//
//import android.os.AsyncTask;
//import android.util.Log;
//
//import com.android.volley.Request;
//import com.android.volley.RequestQueue;
//import com.android.volley.Response;
//import com.android.volley.VolleyError;
//import com.android.volley.toolbox.JsonArrayRequest;
//import com.android.volley.toolbox.Volley;
//
//import org.json.JSONArray;
//
//public class ReuqestSender extends AsyncTask<JSONArray, Void, Void> {
//    @Override
//    protected Void doInBackground(JSONArray... jsonObject) {
//        RequestQueue requestQueue = Volley.newRequestQueue(ReuqestSender.this);
//        JsonArrayRequest jsonArrayRequest = new JsonArrayRequest(Request.Method.POST, DataService.SERVER_URL, JSONArray, new Response.Listener<JSONArray>() {
//            @Override
//            public void onResponse(JSONArray response) {
//                System.out.println("success" + response);
//            }
//        }, new Response.ErrorListener() {
//            @Override
//            public void onErrorResponse(VolleyError error) {
//                Log.d("RESP", "onResponse: " + error);
//            }
//        });
//        requestQueue.add(jsonArrayRequest);
//        requestQueue.cancelAll(jsonArrayRequest);
//        return null;
//    }
//}
