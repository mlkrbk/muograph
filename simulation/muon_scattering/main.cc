#include "Randomize.hh"
#include "G4RunManager.hh"
#include "G4NistManager.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4PVPlacement.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4PhysListFactory.hh"
#include "G4UImanager.hh"
#include "G4UserSteppingAction.hh"
#include "G4Step.hh"
#include "G4Track.hh"
#include "G4EventManager.hh"

#include <array>
#include <fstream>
#include <cmath>
#include <iomanip>
class DetectorConstruction : public G4VUserDetectorConstruction {
public:
    G4VPhysicalVolume* Construct() override {
        auto nist = G4NistManager::Instance();

        auto air = nist->FindOrBuildMaterial("G4_AIR");
        auto iron = nist->FindOrBuildMaterial("G4_Fe");

        auto worldSolid = new G4Box(
            "World", 2*m, 2*m, 2*m
        );

        auto worldLogical = new G4LogicalVolume(
            worldSolid, air, "World"
        );

        auto worldPhysical = new G4PVPlacement(
            nullptr,
            G4ThreeVector(),
            worldLogical,
            "World",
            nullptr,
            false,
            0
        );

        auto blockSolid = new G4Box(
            "IronBlock", 25*cm, 25*cm, 10*cm
        );

        auto blockLogical = new G4LogicalVolume(
            blockSolid, iron, "IronBlock"
        );

        new G4PVPlacement(
            nullptr,
            G4ThreeVector(),
            blockLogical,
            "IronBlock",
            worldLogical,
            false,
            0
        );

        return worldPhysical;
    }
};

class PrimaryGenerator : public G4VUserPrimaryGeneratorAction {
public:
    PrimaryGenerator() {
        gun = new G4ParticleGun(1);

        auto muon = G4ParticleTable::GetParticleTable()
            ->FindParticle("mu-");

        gun->SetParticleDefinition(muon);
        gun->SetParticleEnergy(4*GeV);
        gun->SetParticleMomentumDirection(
            G4ThreeVector(0, 0, -1)
        );

        truth.open("muon_truth.csv");
        truth << std::setprecision(12);

        truth << "event_id,x_true_mm,y_true_mm,z_true_mm,"
              << "dx_true,dy_true,dz_true,energy_true_MeV,"
              << "intersects_iron_geometry\n";
    }

    ~PrimaryGenerator() override {
        truth.close();
        delete gun;
    }

    void GeneratePrimaries(G4Event* event) override {
        const double x = (G4UniformRand() - 0.5) * 60.0 * cm;
        const double y = (G4UniformRand() - 0.5) * 60.0 * cm;

        G4ThreeVector position(x, y, 180*cm);

    // Uniform angular distribution in solid angle,
    // within a cone of 15 degrees around downward vertical.
    const double thetaMax = 15.0 * deg;

    const double cosTheta =
            1.0 - G4UniformRand() * (1.0 - std::cos(thetaMax));

    const double sinTheta =
            std::sqrt(1.0 - cosTheta * cosTheta);

    const double phi = 2.0 * CLHEP::pi * G4UniformRand();

    const G4ThreeVector direction(
            sinTheta * std::cos(phi),
            sinTheta * std::sin(phi),
            -cosTheta
    );

    gun->SetParticleMomentumDirection(direction);
        gun->SetParticlePosition(position);
        gun->GeneratePrimaryVertex(event);

        // Geometrical intersection of the initial vertical ray.
        const bool intersectsIron =
            std::abs(x) <= 25*cm &&
            std::abs(y) <= 25*cm;

        truth
            << event->GetEventID() << ","
            << position.x()/mm << ","
            << position.y()/mm << ","
            << position.z()/mm << ","
            << direction.x() << ","
            << direction.y() << ","
            << direction.z() << ","
            << gun->GetParticleEnergy()/MeV << ","
            << static_cast<int>(intersectsIron) << "\n";
    }

private:
    G4ParticleGun* gun;
    std::ofstream truth;
};

class MuonSteppingAction : public G4UserSteppingAction {
public:
    MuonSteppingAction() {
        output.open("muon_hits.csv");
    output << std::setprecision(12);

        output << "event_id,plane_id,x_mm,y_mm,z_mm,energy_MeV\n";

    boundaries.open("muon_boundaries.csv");
    boundaries << std::setprecision(12);

    boundaries
        << "event_id,boundary,x_mm,y_mm,z_mm,"
        << "dx,dy,dz,energy_MeV\n";
    }

    ~MuonSteppingAction() override {
        output.close();
    boundaries.close();
    }

    void UserSteppingAction(const G4Step* step) override {
        auto track = step->GetTrack();

        // Record only the primary muon.
        if (track->GetParentID() != 0) return;
        if (track->GetDefinition()->GetParticleName() != "mu-") return;

        const auto pre = step->GetPreStepPoint();
        const auto post = step->GetPostStepPoint();

        const auto p0 = pre->GetPosition();
        const auto p1 = post->GetPosition();

    if (post->GetStepStatus() == fGeomBoundary) {

        const auto preVolume = pre->GetPhysicalVolume();
            const auto postVolume = post->GetPhysicalVolume();

            const bool wasIron =
                preVolume && preVolume->GetName() == "IronBlock";

            const bool isIron =
                postVolume && postVolume->GetName() == "IronBlock";

            if (wasIron != isIron) {
                const auto position = post->GetPosition();
                const auto direction = post->GetMomentumDirection();

                const int eventID =
                        G4EventManager::GetEventManager()
                            ->GetConstCurrentEvent()->GetEventID();

                boundaries
                        << eventID << ","
                        << (isIron ? "entry" : "exit") << ","
                        << position.x()/mm << ","
                        << position.y()/mm << ","
                        << position.z()/mm << ","
                        << direction.x() << ","
                        << direction.y() << ","
                        << direction.z() << ","
                        << post->GetKineticEnergy()/MeV << "\n";
            }
    }

        // Detector planes, in mm
    constexpr std::array<double, 6> planes = {
            1400.0, 1000.0, 600.0,
            -600.0, -1000.0, -1400.0
    };

        if (p0.z() == p1.z()) return;

        for (std::size_t i = 0; i < planes.size(); ++i) {
            const double z = planes[i] * mm;

            // Check for a downward crossing.
            if (!(p0.z() > z && p1.z() <= z)) continue;

            // Interpolate crossing along the Geant4 step.
            const double t = (z - p0.z()) / (p1.z() - p0.z());

            const auto crossing = p0 + t * (p1 - p0);

            const double energy =
                pre->GetKineticEnergy() +
                t * (post->GetKineticEnergy() - pre->GetKineticEnergy());

            const int eventID =
                G4EventManager::GetEventManager()
                    ->GetConstCurrentEvent()->GetEventID();

            output
                << eventID << ","
                << i << ","
                << crossing.x() / mm << ","
                << crossing.y() / mm << ","
                << crossing.z() / mm << ","
                << energy / MeV << "\n";
        }
    }

private:
    std::ofstream output;
    std::ofstream boundaries;
};
int main(int argc, char** argv) {
    auto runManager = new G4RunManager;

    runManager->SetUserInitialization(new DetectorConstruction);

    G4PhysListFactory factory;
    auto physics = factory.GetReferencePhysList("FTFP_BERT");
    runManager->SetUserInitialization(physics);

    runManager->SetUserAction(new PrimaryGenerator);
    runManager->SetUserAction(new MuonSteppingAction);
    runManager->Initialize();

    auto ui = G4UImanager::GetUIpointer();

    if (argc > 1) {
        ui->ApplyCommand(G4String("/control/execute ") + argv[1]);
    } else {
        ui->ApplyCommand("/run/beamOn 10");
    }
    delete runManager;
    return 0;
}
