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

### Advanced enhancements
* Account for fewer stops during low-traffic times
* Holiday detection (switch to sunday schedule on holidays)

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

### Dependency injection? I feel dirty.

You're telling me, now imagine writing a framework _based_ on dependency injection.

Typically, when one imagines dependency injection, it's used to loosen requirements
and get around limitations of static languages, much to the chagrin of future maintainers.

With Workles, dependency injection is used to _guarantee_ more. It resolves arguments when
you create the application, to make sure your application has no url or endpoint typos and
your middlewares all play well together. We take maximum advantage of Python's introspective
capabilities to eliminate common errors and ensure that a compiled application is as
solid as we can know.

If it helps, think of it as function-level imports.

If you're a fan of functional programming, this all amounts to more type-checking and
single-assignment parameters, along with decreased mutability and the near-elimination
of global state (from the framework, anyway).

### I see code generation. Why do I see code generation.

Yes, the middleware stack is indeed code-generated and compiled at Application creation time.

Code generation is by and large, a really bad code smell, especially in dynamic languages.
Code generation became necessary because, excepting versions newer than PEP 362, Python does not
have a way to modify function signatures. In fact, code generation offered several benefits over
the initial 100% dynamic resolution implementation:
  * More stringent checking of middleware stack structure
  * Lower middleware execution overhead (faster response times)
  * Cleaner stack traces
  * More compact and maintainable code in the framework itself (including generated code)
  * next() accepts mixtures of positional and keyword arguments just like standard Python
  * next() becomes introspectable again (not possible with standard decorators or partials)

If you still have doubts, check out collections.namedtuple and the third-party decorator module.
The respective authors have laid out very good reasons for using code generation.
