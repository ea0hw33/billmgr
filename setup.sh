#!/bin/bash

cp /usr/local/mgr5/lib/python/billmgr_mod_testpayment.xml /usr/local/mgr5/etc/xml/
ln -s /usr/local/mgr5/lib/python/pmtestpayment.py /usr/local/mgr5/paymethods/pmtestpayment
ln -s /usr/local/mgr5/lib/python/testpayment.py /usr/local/mgr5/cgi/testpayment