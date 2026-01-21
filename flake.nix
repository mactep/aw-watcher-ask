{
  description = "ActivityWatch watcher that asks the user questions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        aw-watcher-ask = (pkgs.callPackage ./default.nix { }).aw-watcher-ask;
      in
      {
        packages = {
          default = aw-watcher-ask;
        };

        devShells = {
          default = pkgs.mkShell {
            inputsFrom = [ aw-watcher-ask ];
            packages = [
              pkgs.poetry
              pkgs.python3Packages.pytest
              pkgs.python3Packages.pip
            ];
            shellHook = ''
              python3 -m venv .venv
              source .venv/bin/activate
            '';
          };
        };
      }
    );
}
