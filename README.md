# ETAVTA

## Features
* VTA schedule parsing
* Fancy types for representing Trains, Stops, Timetables, etc.
* Stop time interpolation for stations that are implicit (i.e., not
  present in the schedules)

## TODO
* Code breakup
* More repr functions
* Automated schedule fetching
* Command-line interface (with options and whatnot)
* An actual web site
* More documentation
* Tests
* Output schedules in a sane format for posterity

## Inconsistencies in the VTA schedule format

### Timing inconsistencies
* 901 North (Alum Rock) Express trains are denoted by missing times from Capitol and Tamien, inclusive.
  However, missing times do not always mean the train will not stop at an inferred station when
  an explicit station is left blank. E.g., non-express trains stop at Cisco Way prior to the Great Mall.
* Trains will stop at unscheduled stations before going out of service (Southbound Winchester trains
  go out of service at Gish).
* Only one route (901) has departure times listed, and in only one direction,
  for two stations, for a few hours.
* There are separate but identical schedules for Saturday and Sunday.
* Schedules are 'daily', but 1:00AM Monday is on the Sunday schedule.

### Naming inconsistencies
* Abbreviation
   * 'Station' vs 'Sta.'
   * 'Stn.' vs 'Sta.'
* The full names of stations vary between:
   * '<station name> Station'
   * '<station name> Light Rail Station'
   * '<station name> Transit Center'
   * '<station name> Transit Ctr'
   * and just '<station name>'

## Workles

* Certainly not the worst web framework
* Actually it's pretty alright
* The web framework that partial() built (partial()-ly built?)
