class Urace < Formula
  include Language::Python::Virtualenv

  desc "AI-powered product improvement runtime with P2P feature exchange"
  homepage "https://github.com/joaoalbertocsjunior/URACE"
  url "https://files.pythonhosted.org/packages/source/u/urace/urace-0.6.0.tar.gz"
  sha256 "f4d11c4f73f44323942a9f996bd33e53c03ce09fb6d9ce74254fecaf0c6955b4"
  license "Apache-2.0"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/urace", "--version"
  end
end
