{ pkgs }: {
  deps = [
    pkgs.libopus
    pkgs.ffmpeg-full
		pkgs.nodePackages.prettier
    pkgs.postgresql
  ];
  env = {
  
  PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.libopus
  ];};
}