used it with the starttime equal to the current hour, seems like 1hr granuality

**observations**

https://opendata.fmi.fi/wfs?service=WFS\&version=2.0.0\&request=getFeature\&storedquery\_id=fmi::observations::weather::hourly::simple\&fmisid=108040\&starttime=2026-03-04T20:00:00Z

https://opendata.fmi.fi/wfs?service=WFS\&version=2.0.0\&request=getFeature\&storedquery\_id=fmi::observations::weather::hourly::simple\&fmisid=108040\&starttime=2026-03-04T20:00:00Z\&**parameters=TA\_PT1H\_AVG  --> if only want avg temperature**





**forercast**

yle website@9am: -4

google@8am: -7

https://opendata.fmi.fi/wfs?service=WFS\&version=2.0.0\&request=getFeature\&storedquery\_id=**fmi::forecast::edited::weather::scandinavia::point::simple**\&fmisid=108040\&starttime=2026-03-05T07:00:00Z\&endtime=2026-03-05T07:00:00Z\&parameters=temperature  -->-4.73

https://opendata.fmi.fi/wfs?service=WFS\&version=2.0.0\&request=getFeature\&storedquery\_id=**fmi::forecast::harmonie::surface::point::simple**\&fmisid=108040\&starttime=2026-03-05T07:00:00Z\&endtime=2026-03-05T07:00:00Z\&parameters=temperature  -->-4

https://opendata.fmi.fi/wfs?service=WFS\&version=2.0.0\&request=getFeature\&storedquery\_id=**fmi::forecast::meps::surface::point::simple**\&fmisid=108040\&starttime=2026-03-05T07:00:00Z\&endtime=2026-03-05T07:00:00Z\&parameters=temperature  -->-4

https://opendata.fmi.fi/wfs?service=WFS\&version=2.0.0\&request=getFeature\&storedquery\_id=**ecmwf::forecast::surface::point::simple**\&fmisid=108040\&starttime=2026-03-05T07:00:00Z\&endtime=2026-03-05T07:00:00Z\&parameters=temperature   -->-6.5



