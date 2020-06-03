/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2014-2020,  The University of Memphis
 *
 * This file is part of NDNSD.
 * Author: Saurab Dulal (sdulal@memphis.edu)
 *
 * NDNSD is free software: you can redistribute it and/or modify it under the terms
 * of the GNU Lesser General Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later version.
 *
 * NDNSD is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
 * without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
 * PURPOSE.  See the GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License along with
 * NDNSD, e.g., in COPYING.md file.  If not, see <http://www.gnu.org/licenses/>.
 **/

#include<iostream>
#include "ndnsd/discovery/service-discovery.hpp"
#include <list>

#include <boost/program_options/options_description.hpp>
#include <boost/program_options/variables_map.hpp>
#include <boost/program_options/parsers.hpp>

static void
usage(const boost::program_options::options_description& options)
{
  std::cout << "Usage: ndnsd-consumer [options] e.g. printer \n"
            << options;
   exit(2);
}
static ndn::time::milliseconds
getDefaultPingInterval()
{
  return ndn::time::milliseconds(1000);
}

class Consumer
{
public:
  Consumer(const ndn::Name& serviceName, const std::map<char, uint8_t>& pFlags)
   : m_serviceDiscovery(serviceName, pFlags, std::bind(&Consumer::processCallback, this, _1))
  {
  }

  void
  execute ()
  {
    // process and handle request
    m_serviceDiscovery.consumerHandler();
  }

private:
  void
  processCallback(const ndnsd::discovery::Reply& callback)
  {
    auto status = (callback.status == ndnsd::discovery::ACTIVE)? "ACTIVE": "EXPIRED";

    std::cout << "Status: " << status << std::endl;
    for (const auto& item : callback.serviceDetails)
    {
      std::cout << item.first << ": " << item.second << std::endl;
    }
  }

private:
  ndnsd::discovery::ServiceDiscovery m_serviceDiscovery;

};


int
main(int argc, char* argv[])
{

  std::string serviceName;
  int contFlag = -1;
  ndn::time::milliseconds interval;

  namespace po = boost::program_options;
  po::options_description visibleOptDesc("Options");

  visibleOptDesc.add_options()
    ("help,h",      "print this message and exit")
    // ("interval,i",  po::value<ndn::time::milliseconds::rep>()->default_value(getDefaultPingInterval().count()),
    //                 "request interval, in milliseconds")
    ("serviceName,s", po::value<std::string>(&serviceName)->required(), "Service name to fetch service info")
    ("continuous,c", po::value<int>(&contFlag), "continuous discovery, 1 for true 0 for false")
  ;

  try
  {
    po::variables_map optVm;
    po::store(po::parse_command_line(argc, argv, visibleOptDesc), optVm);
    po::notify(optVm);

    if (optVm.count("continuous")) {
        if (contFlag != ndnsd::discovery::OPTIONAL and contFlag != ndnsd::discovery::REQUIRED) 
        {
          std::cout << "'c' must be either '0' or '1', default i.e. '0' will be used" << std::endl;
        }
      }
    else
      contFlag = 0;

    if (optVm.count("serviceName")) {
      if (serviceName.empty())
      {
        std::cerr << "ERROR: serviceName cannot be empty" << std::endl;
        usage(visibleOptDesc);
      }
    }

  }
  catch (const po::error& e) {
    std::cerr << "ERROR: " << e.what() << std::endl;
    usage(visibleOptDesc);
  }
  // TODO: protocol shouldn't be hard-coded.
  std::map<char, uint8_t> flags;
  flags.insert(std::pair<char, uint8_t>('p', ndnsd::SYNC_PROTOCOL_PSYNC)); //protocol choice
  flags.insert(std::pair<char, uint8_t>('t', ndnsd::discovery::CONSUMER)); //type producer: 1
  flags.insert(std::pair<char, uint8_t>('c', contFlag));

  try
  {
    std::cout << "Fetching service info for: " << serviceName << std::endl;
    Consumer consumer(serviceName, flags);
    consumer.execute();
  }
  catch (const std::exception& e) {
    std::cerr << "ERROR: " << e.what() << std::endl;
  }

}