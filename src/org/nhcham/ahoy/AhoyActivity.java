package org.nhcham.ahoy;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.net.wifi.*;
import android.os.*;
import android.text.*;
import android.util.Log;
import android.view.*;
import android.view.animation.Animation;
import android.view.animation.Transformation;
import android.view.LayoutInflater;
import android.view.View.OnClickListener;
import android.widget.*;
import android.widget.LinearLayout.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.Comparator;

import org.nhcham.ahoy.AhoyService;
import org.nhcham.ahoy.ApMessageFilter;

public class AhoyActivity extends Activity implements OnClickListener 
{
    private static final String TAG = "AhoyActivity";
    
    LinearLayout messagesLayout, messagesLayoutInactive;
    TextView currentBroadcast, previouslySeenHeader, noMessagesIndicator;
    ProgressBar broadcastSpinner;
    String statusMessage;
    Set<View> messageViews;
    LayoutInflater inflater;
    
    EditText editText;
    ProgressBar capacity;
    
    AhoyService ahoyService;
    boolean boundService;
    
    UpdateReceiver updateReceiver;
    
    private class UpdateReceiver extends BroadcastReceiver 
    {
        AhoyActivity ahoyActivity;

        public UpdateReceiver(AhoyActivity _ahoyActivity) 
        {
            super();
            ahoyActivity = _ahoyActivity;
        }

        @Override
        public void onReceive(Context c, Intent intent) 
        {
            ahoyActivity.handleUpdate(intent);
        }
    };
    
    @Override
    public void onCreate(Bundle savedInstanceState) 
    {
//         Log.d(TAG, "onCreate()");
        super.onCreate(savedInstanceState);
        this.requestWindowFeature(Window.FEATURE_NO_TITLE);
        setContentView(R.layout.main);
        
        messagesLayout = (LinearLayout) findViewById(R.id.messagesLayout);
        messagesLayoutInactive = (LinearLayout) findViewById(R.id.messagesLayoutInactive);
        currentBroadcast = (TextView) findViewById(R.id.currentBroadcast);
        broadcastSpinner = (ProgressBar) findViewById(R.id.broadcastSpinner);
        previouslySeenHeader = (TextView) findViewById(R.id.previouslySeenHeader);
        noMessagesIndicator = (TextView) findViewById(R.id.noMessagesIndicator);
        inflater = (LayoutInflater) getSystemService(Context.LAYOUT_INFLATER_SERVICE);
        
        findViewById(R.id.buttonBroadcastMessage).setOnClickListener(this);
        findViewById(R.id.buttonStopBroadcast).setOnClickListener(this);
        findViewById(R.id.buttonStopBroadcast).setVisibility(View.GONE);

        updateReceiver = new UpdateReceiver(this);
        
        startService(new Intent(AhoyActivity.this, AhoyService.class));
    }        
    
    @Override
    public void onStart()
    {
//         Log.d(TAG, "onStart()");
        super.onStart();
        Intent intent = new Intent(this, AhoyService.class);
        bindService(intent, serviceConnection, BIND_AUTO_CREATE);
    }
    
    @Override
    public void onResume()
    {
//         Log.d(TAG, "onResume()");
        super.onResume();
        registerReceiver(updateReceiver, new IntentFilter("AhoyActivityUpdate"));
        if (ahoyService != null)
        {
            ahoyService.queryState();
            ahoyService.performScan();
        }
    }
    
    @Override
    public void onPause()
    {
//         Log.d(TAG, "onPause()");
        super.onPause();
        unregisterReceiver(updateReceiver);
    }
    
    ServiceConnection serviceConnection = new ServiceConnection() 
    {
        public void onServiceConnected(ComponentName name, IBinder service)
        {
            boundService = true;
            AhoyService.LocalBinder binder = (AhoyService.LocalBinder)service;
            ahoyService = binder.getServerInstance();        
        }
        
        public void onServiceDisconnected(ComponentName name)
        {
            boundService = false;
            ahoyService = null;
        }
    };

    @Override
    public void onStop() 
    {
//         Log.d(TAG, "onStop()");
        super.onStop();
        if (boundService)
        {
            unbindService(serviceConnection);
            boundService = false;
        }
    }
    
    @Override
    public boolean onCreateOptionsMenu(Menu menu)
    {
        MenuInflater menuInflater = getMenuInflater();
        menuInflater.inflate(R.layout.menu, menu);
        return true;
    }
       
    @Override
    public boolean onOptionsItemSelected(MenuItem item)
    {
         
        switch (item.getItemId()) 
        {
            case R.id.menu_shutdown:
                showDialog(this, this.getString(R.string.are_you_sure_you_want_to_shut_down), null, this.getString(R.string.shut_down), new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which)
                    {
                        stopService(new Intent(AhoyActivity.this, AhoyService.class));
                        finish();
                    }
                });
                return true;
        }
        return false;
    }
            
    public AlertDialog showDialog(Activity activity, String message, View view, String positiveLabel, DialogInterface.OnClickListener positiveListener) {
        AlertDialog.Builder builder = new AlertDialog.Builder(activity);
        return builder.setMessage(message)
            .setCancelable(true)
            .setView(view)
            .setPositiveButton(positiveLabel, positiveListener) 
            .setNegativeButton(this.getString(R.string.cancel), new DialogInterface.OnClickListener() {
                public void onClick(DialogInterface dialog, int id) {
                    dialog.cancel();
                }
            }).show();
    }
    
    public void onClick(View view) 
    {
        // check whether it's a message that got clicked
        if (messageViews != null && messageViews.contains(view))
        {
            for (View v : messageViews)
            {
                int which = (v == view) ? View.VISIBLE : View.GONE;
                int style = (v == view) ? Typeface.BOLD : Typeface.NORMAL;
                ((TextView)v.findViewById(R.id.message)).setTypeface(null, style);
                v.findViewById(R.id.details).setVisibility(which);
                v.findViewById(R.id.buttonShareMessage).setVisibility(which);
            }
        }
        else if (view.getId() == R.id.buttonShareMessage)
        {
            View parent = (View)view.getParent();
            if (parent != null)
            {
                TextView messageView = (TextView)parent.findViewById(R.id.message);
                final String message = messageView.getText().toString();
                showDialog(this, String.format(this.getString(R.string.are_you_sure_you_want_to_repeat_message), message), 
                null, this.getString(R.string.repeat_message), new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which)
                    {
                        ahoyService.broadcastMessage(message);
                    }
                });
                
            }
        }
        else if (view.getId() == R.id.buttonBroadcastMessage)
        {
            InputFilter bitLengthFilter = new InputFilter() 
            {
                @Override
                public CharSequence filter(CharSequence source, int sstart, int send, Spanned destination, int dstart, int dend)
                {
                    StringBuffer buffer = new StringBuffer();
                    buffer.append(destination, 0, dstart);
                    buffer.append(source, sstart, send);
                    buffer.append(destination, dend, destination.length());
                    final String s = buffer.toString();
                    
                    int[] result = ahoyService.messageFilter.encodeMessage(s);
                    
                    int bitLength = result[0];
                    
                    if (bitLength >= 0)
                    {
                        if (bitLength > ApMessageFilter.MAX_BITS)
                        {
                            // This message would exceed the maximum capacity.
                            // Now cut the message so that it fits.
                            int lastBitLength = 0;
                            for (int i = sstart; i < send - 1; i++)
                            {
                                buffer = new StringBuffer();
                                buffer.append(destination, 0, dstart);
                                buffer.append(source, sstart, i);
                                buffer.append(destination, dend, destination.length());
                                final String s2 = buffer.toString();
                                
                                result = ahoyService.messageFilter.encodeMessage(s2);
                                
                                bitLength = result[0];
//                                 Log.d(TAG, String.format("Trying [%s]: %d bits", s2, bitLength));
                                // if this exceeds the maximum capacity, return
                                // the last thing that worked
                                if (bitLength > ApMessageFilter.MAX_BITS)
                                {
                                    if (sstart == i)
                                        return "";
                                    else
                                    {
                                        return source.subSequence(sstart, i);
                                    }
                                }
                                lastBitLength = bitLength;
                            }
                            return "";
                        }
                    }
                        
                    return null;
                }
            };
                
            View t = inflater.inflate(R.layout.enter_message, null);
            capacity = (ProgressBar)t.findViewById(R.id.capacity);
            capacity.setMax(ApMessageFilter.MAX_BITS);
            capacity.setProgress(0);

            editText = (EditText)t.findViewById(R.id.message);
//             editText.setFilters(new InputFilter[]{ bitLengthFilter });
            editText.setText("");
            
            final AlertDialog enterMessageDialog = showDialog(this, this.getString(R.string.enter_a_message_colon), t, this.getString(R.string.broadcast), new DialogInterface.OnClickListener() {
                public void onClick(DialogInterface dialog, int which)
                {
                    final String message = editText.getText().toString().trim();
                    if (message.length() > 0)
                    {
//                         Log.d(TAG, String.format("Broadcasting a new message: %s", message));
                        ahoyService.broadcastMessage(message);
                    }
                }
            });
            
            editText.addTextChangedListener(new TextWatcher() {
                public void afterTextChanged(Editable _s)
                {
                    String s = _s.toString();
                    int[] result = ahoyService.messageFilter.encodeMessage(s);
                    int bitLength = result[0];
                    boolean canBroadcast = false;
                    if (bitLength >= 0)
                    {
                        capacity.setProgress(bitLength);
                        canBroadcast = (bitLength <= ApMessageFilter.MAX_BITS);
                    }
                    else
                    {
                        capacity.setProgress(capacity.getMax());
                        canBroadcast = false;
                    }
                    if (enterMessageDialog != null)
                        enterMessageDialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(canBroadcast);
                }
                public void beforeTextChanged(CharSequence s, int start, int count, int after){}
                public void onTextChanged(CharSequence s, int start, int before, int count){}
            }); 

        }
        else if (view.getId() == R.id.buttonStopBroadcast)
        {
            showDialog(this, this.getString(R.string.are_you_sure_you_want_to_stop_broadcasting), null, 
            this.getString(R.string.stop_broadcast), new DialogInterface.OnClickListener() {
                public void onClick(DialogInterface dialog, int which)
                {
                    ahoyService.stopBroadcast();
                }
            });
        }
    }

    public void handleUpdate(Intent intent)
    {
//         Log.d(TAG, "handleUpdate()");
        
        if (intent.getAction().equals("AhoyActivityUpdate"))
            refresh(intent);
    }
    
    private String formatDuration(long duration_seconds)
    {
        long minutes = duration_seconds / 60;
        long hours = minutes / 60;
        long days = hours / 24;
        long weeks = days / 7;
        long years = days / 365;
        if (minutes < 1)
            return String.format(this.getString(R.string.duration_lt_1m));
        else if (hours < 1)
            return minutes == 1 ? this.getString(R.string.duration_1m_ago) : String.format(this.getString(R.string.duration_nm_ago), minutes);
        else if (days < 1)
            return hours == 1 ? this.getString(R.string.duration_1h_ago) : String.format(this.getString(R.string.duration_nh_ago), hours);
        else if (weeks < 1)
            return days == 1 ? this.getString(R.string.duration_1d_ago) : String.format(this.getString(R.string.duration_nd_ago), days);
        else if (years < 1)
            return weeks == 1 ? this.getString(R.string.duration_1w_ago) : String.format(this.getString(R.string.duration_nw_ago), weeks);
        else
            return years == 1 ? this.getString(R.string.duration_1y_ago) : String.format(this.getString(R.string.duration_ny_ago), weeks);
    }
    
    public void refresh(Intent intent)
    {
//         Log.d(TAG, "refresh()");

        if (intent.hasExtra("currentlyBroadcasting"))
        {
            String currentlyBroadcasting = intent.getStringExtra("currentlyBroadcasting");
            
            if (currentlyBroadcasting == null)
            {
                currentBroadcast.setText(this.getString(R.string.paren_nothing_paren));
                findViewById(R.id.buttonStopBroadcast).setVisibility(View.GONE);
            }
            else
            {
                currentBroadcast.setText(currentlyBroadcasting);
                findViewById(R.id.buttonStopBroadcast).setVisibility(View.VISIBLE);
            }
        }
        
        if (intent.hasExtra("showSpinner"))
        {
            boolean showSpinner = intent.getBooleanExtra("showSpinner", false);
            broadcastSpinner.setVisibility(showSpinner ? View.VISIBLE : View.GONE);
        }
        
        if (intent.hasExtra("messageHash"))
        {
            // clear message views
            if (messageViews == null)
                messageViews = new HashSet<View>();
            messagesLayout.removeAllViews();
            messagesLayoutInactive.removeAllViews();
            messageViews.clear();
            
            HashMap<String, HashMap<String, Long> > messageHash = (HashMap<String, HashMap<String, Long> >)intent.getSerializableExtra("messageHash");
            
            if (messageHash != null)
            {
                final long currentTime = System.currentTimeMillis();
            
                // mark messages as active or non-active based on current timr
                for (HashMap<String, Long> values : messageHash.values())
                {
                    values.put("active", new Long((currentTime - values.get("lastSeen")) < AhoyService.ACTIVE_TIMEOUT * 1000 ? 1 : 0));
                    values.put("firstSeenDiff", new Long(currentTime - values.get("firstSeen")));
                    values.put("lastSeenDiff", new Long(currentTime - values.get("lastSeen")));
                }
                    
                // sort keys
                ArrayList<String> keys = new ArrayList<String>();
                for (String key : messageHash.keySet())
                    keys.add(key);
                    
                class MessageComparator implements Comparator<String> {
                    private HashMap<String, HashMap<String, Long> > messageHash;
                    MessageComparator(HashMap<String, HashMap<String, Long> > _messageHash)
                    {
                        messageHash = _messageHash;
                    }
                    
                    private int clipDiff(long a, long b)
                    {
                        long diff = a - b;
                        if (diff < 0)
                            return -1;
                        else if (diff > 0)
                            return 1;
                        else
                            return 0;
                    }
                    
                    public int compare(String a, String b)
                    {
                        int activeDiff = clipDiff(messageHash.get(b).get("active"), messageHash.get(a).get("active"));
                        if (activeDiff == 0)
                        {
                            int isActive = messageHash.get(a).get("active").intValue();
                            if (isActive == 1)
                            {
                                int firstSeenDiff = clipDiff(messageHash.get(a).get("firstSeenDiff"), messageHash.get(b).get("firstSeenDiff"));
                                if (firstSeenDiff == 0)
                                    return clipDiff(messageHash.get(b).get("level"), messageHash.get(a).get("level"));
                                else
                                    return firstSeenDiff;
                            }
                            else
                            {
                                int lastSeenDiff = clipDiff(messageHash.get(a).get("lastSeenDiff"), messageHash.get(b).get("lastSeenDiff"));
                                if (lastSeenDiff == 0)
                                    return clipDiff(messageHash.get(b).get("level"), messageHash.get(a).get("level"));
                                else
                                    return lastSeenDiff;
                            }
                        }
                        else
                            return activeDiff;
                    }
                };
                    
                java.util.Collections.sort(keys, new MessageComparator(messageHash));
                
                LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(LayoutParams.FILL_PARENT, LayoutParams.WRAP_CONTENT);
                boolean seenSomethingActive = false;
                boolean seenSomethingInactive = false;
                for (String message: keys)
                {
                    View t = inflater.inflate(R.layout.message, null);
                    TextView messageView = (TextView)t.findViewById(R.id.message);
                    messageView.setText(message);
                    
                    TextView countLabel = (TextView)t.findViewById(R.id.count);
                    if (messageHash.get(message).get("count") > 1)
                        countLabel.setText(String.format("%d", messageHash.get(message).get("count")));
                    
                    int level = messageHash.get(message).get("level").intValue();
                    if (level <= -1000)
                        ((ImageView)t.findViewById(R.id.icon)).setImageResource(R.drawable.wifi_0);
                    else if (level <= -90)
                        ((ImageView)t.findViewById(R.id.icon)).setImageResource(R.drawable.wifi_1);
                    else if (level <= -80)
                        ((ImageView)t.findViewById(R.id.icon)).setImageResource(R.drawable.wifi_2);
                    else if (level <= -60)
                        ((ImageView)t.findViewById(R.id.icon)).setImageResource(R.drawable.wifi_3);
                    else if (level <= -10)
                        ((ImageView)t.findViewById(R.id.icon)).setImageResource(R.drawable.wifi_4);

                    if (messageHash.get(message).get("active") == 0)
                    {
                        seenSomethingInactive = true;
                        ((TextView)t.findViewById(R.id.details)).setText(this.getString(R.string.last_seen) + " " + formatDuration((currentTime - messageHash.get(message).get("lastSeen")) / 1000));
                        messagesLayoutInactive.addView(t);
                    }
                    else
                    {
                        seenSomethingActive = true;
                        ((TextView)t.findViewById(R.id.details)).setText(this.getString(R.string.first_seen) + " " + formatDuration((currentTime - messageHash.get(message).get("firstSeen")) / 1000));
                        messagesLayout.addView(t);
                    }
                    messageViews.add(t);
                    t.setOnClickListener(this);
                    t.findViewById(R.id.buttonShareMessage).setOnClickListener(this);
                }
                previouslySeenHeader.setVisibility(seenSomethingInactive ? View.VISIBLE : View.GONE);
                noMessagesIndicator.setVisibility(seenSomethingActive ? View.GONE : View.VISIBLE);
            }
        }
    }
}
