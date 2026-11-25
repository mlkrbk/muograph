cmake_minimum_required(VERSION 3.16)

project(MuonScattering)

find_package(Geant4 REQUIRED)

add_executable(muon_sim main.cc)

target_link_libraries(muon_sim PRIVATE ${Geant4_LIBRARIES})

target_include_directories(muon_sim PRIVATE ${Geant4_INCLUDE_DIRS})

target_compile_features(muon_sim PRIVATE cxx_std_17)
